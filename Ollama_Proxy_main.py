import os
import time
import uuid
import hashlib
import httpx
import asyncio
from fastapi import FastAPI, Request, HTTPException, Path, Query
from fastapi.responses import JSONResponse
import aiomysql

from ndjson_parser import ensure_schema, assemble_ndjson_text_and_store, store_request_summary
import logging
from logging.handlers import RotatingFileHandler
from urllib.parse import urljoin#version 109
import re

_SAFE_PATH_RE = re.compile(r"^/[-A-Za-z0-9_./%]*$")#version 109

def get_action_path(agent: str, action: str) -> str:#version 109
    if agent in AGENT_OVERRIDES and action in AGENT_OVERRIDES[agent]:
        return AGENT_OVERRIDES[agent][action]
    if action in AGENT_ENDPOINTS:
        return AGENT_ENDPOINTS[action]
    raise HTTPException(status_code=400, detail="Unknown action")

def compose_upstream(agent: str, path: str) -> str:#version 109
    base = AGENT_URLS.get(agent)
    if not base:
        raise HTTPException(status_code=400, detail="Unknown agent")
    return urljoin(base.rstrip("/") + "/", path.lstrip("/"))


LOG_PATH = "/opt/ollama_proxy/proxy_main.log"

logger = logging.getLogger("ollama_proxy_main")
logger.setLevel(logging.INFO)

handler = RotatingFileHandler(LOG_PATH, maxBytes=5_000_000, backupCount=3)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
handler.setFormatter(formatter)

if not logger.handlers:
    logger.addHandler(handler)

AGENT_URLS = {#version 109
    "pixatrail": os.getenv("OLLAMA_PIXATRAIL_URL", "http://127.0.0.1:7860"),
    "ollama-dev": os.getenv("OLLAMA_DEV_URL", "http://127.0.0.1:7861"),
    "ollama-qwen": os.getenv("OLLAMA_QWEN_URL", "http://127.0.0.1:11440"),
}

# Only the actions you actually use (no 'models' entry)
AGENT_ENDPOINTS = {#version 109
    "generate": "/api/generate",        # default
    "data_list": "/agent/data",
    "data_messages": "/agent/data/messages",
    "data_last": "/agent/data/last",
    "delete": "/agent/data"             # DELETE with ?conversation_title=...
}

# Per-agent overrides for actions that differ from the default
AGENT_OVERRIDES = {#version 109
    "pixatrail": { "generate": "/api/generate" },   # pixatrail uses /api/generate
    "ollama-dev": { "generate": "/generate" },      # dev agent uses /api/generate
    "ollama-qwen": { "generate": "/generate" }      # qwen uses /generate (no /api/)
}

def resolve_upstream(agent_name: str):
    if not agent_name:
        return None
    if agent_name not in AGENT_URLS:
        raise HTTPException(status_code=400, detail="Unknown agent")
    return AGENT_URLS[agent_name]


DB = {
    "host": os.getenv("OLLAMA_DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("OLLAMA_DB_PORT", "3306")),
    "user": os.getenv("OLLAMA_DB_USER", "proxy"),
    "password": os.getenv("OLLAMA_DB_PASSWORD", ""),
    "db": os.getenv("OLLAMA_DB_NAME", "ollama_proxy"),
    "autocommit": True
}

# Validate at startup
if not DB["password"]:
    logger.error("Database password not set in OLLAMA_DB_PASSWORD")
    raise RuntimeError("Missing DB password environment variable OLLAMA_DB_PASSWORD")

async def get_conn():
    return await aiomysql.connect(**DB)


IDLE_TIMEOUT = float(os.getenv("OLLAMA_IDLE_TIMEOUT", "5"))

app = FastAPI(title="Ollama Proxy Collector")

@app.on_event("startup")
async def startup():
    await ensure_schema()

@app.post("/generate")
async def generate(request: Request):
    body = await request.json()
    agent = body.get("agent")
    if not agent:
        raise HTTPException(status_code=400, detail="agent required")

    # conversation_title from client (optional but forwarded and returned)
    conversation_title = body.get("conversation_title")

    # Get prompt and model early
    prompt = body.get("prompt", "")
    model = body.get("model", "unknown")

    # action or raw path selection (prefer action)
    action = body.get("action")
    client_path = body.get("path")

    # Decide path: prefer action, fallback to client_path, default to 'generate'
    if action:
        try:
            path = get_action_path(agent, action)
        except HTTPException:
            raise
    elif client_path:
        if not isinstance(client_path, str) or not client_path.startswith("/"):
            raise HTTPException(status_code=400, detail="path must start with '/'")
        if ".." in client_path or not _SAFE_PATH_RE.match(client_path):
            raise HTTPException(status_code=400, detail="invalid path")
        path = client_path
    else:
        path = get_action_path(agent, "generate")

    # Compose upstream URL safely
    upstream = compose_upstream(agent, path)

    # Ensure conversation_title is present in forwarded body if provided
    if conversation_title:
        body["conversation_title"] = conversation_title

    # Save local prompt immediately (only for new prompts from now on)
    local_prompt_id = await save_prompt_local(conversation_title, prompt, model)

    # Build summary chain using conversation_title
    summary_chain = await build_summary_chain(conversation_title)

    if summary_chain:
        # continuing conversation
        combined_prompt = (
            summary_chain +
            'Now the user asks:\n"' +
            prompt +
            '"'
        )
        logger.info(f"Summary chain applied for conversation_title={conversation_title}")
    else:
        # new conversation → no summary context
        combined_prompt = prompt
        logger.info(f"No summary chain applied for conversation_title={conversation_title}")

    body["prompt"] = combined_prompt

    req_id = str(uuid.uuid4())
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    start = time.time()
    full = ""
    tokens = 0
    done = False
    idle_timed_out = False
    upstream_status = None

    async with httpx.AsyncClient(timeout=None) as client:
        try:
            async with client.stream("POST", upstream, json=body) as resp:
                upstream_status = resp.status_code
                if resp.status_code >= 400:
                    _ = await resp.aread()
                    raise HTTPException(status_code=502, detail=f"Upstream error: {resp.status_code}")

                full, tokens, done, idle_timed_out = await assemble_ndjson_text_and_store(
                    resp, req_id, idle_timeout=IDLE_TIMEOUT, agent=agent
                )
        except httpx.RequestError as e:
            logger.error(f"Upstream request failed for {req_id}: {e}")
            raise HTTPException(status_code=502, detail=f"Upstream request failed: {str(e)}")

    end = time.time()

    # Store request summary / metrics as before
    try:
        await store_request_summary(req_id, model, prompt_hash, start, end, tokens, agent=agent, conversation_title=conversation_title)
    except TypeError:
        await store_request_summary(req_id, model, prompt_hash, start, end, tokens, agent=agent)

    # Build response object and include local conversation id
    result = {
        "request_id": req_id,
        "model": model,
        "agent": agent,
        "conversation_title": conversation_title,
        "tokens": tokens,
        "latency_ms": int((end - start) * 1000),
        "text": full,
        "done": bool(done),
        "idle_timed_out": bool(idle_timed_out),
        "prompt_preview": (prompt[:500] + "...") if len(prompt) > 500 else prompt,
        "upstream_status": upstream_status,
        # expose local prompt id as conversation_id so UI can reference it if needed
        "conversation_id": local_prompt_id
    }

    # Update local prompt with upstream id and full response
    # upstream may return an id in NDJSON stream or headers; try to extract it from result of assemble_ndjson_text_and_store
    # If you have upstream id elsewhere, pass it here. For now we set upstream_id to req_id as fallback.
    upstream_id = req_id
    await update_prompt_local(local_prompt_id, upstream_id, full)

    # Generate and store summary using local_prompt_id
    summary_result = await run_summary(
        prompt=prompt,
        llm_response=full,
        req_id=req_id,
        conversation_title=conversation_title,
        model=model,
        prompt_id=local_prompt_id
    )

    if summary_result is None:
        logger.error(f"Summary failed for req_id={req_id}")
    else:
        logger.info(f"Summary OK for req_id={req_id}: {summary_result}")

    if idle_timed_out:
        return JSONResponse(result, status_code=502)

    return JSONResponse(result)



@app.get("/stats")
async def stats():
    conn = await get_conn()
    cur = await conn.cursor()

    await cur.execute("""
        SELECT COUNT(*), AVG(latency_ms), SUM(tokens),
               MIN(latency_ms), MAX(latency_ms)
        FROM requests
    """)

    row = await cur.fetchone()
    await cur.close()
    conn.close()

    return {
        "total_requests": int(row[0] or 0),
        "avg_latency_ms": float(row[1]) if row[1] is not None else None,
        "total_tokens": int(row[2] or 0),
        "min_latency_ms": int(row[3]) if row[3] is not None else None,
        "max_latency_ms": int(row[4]) if row[4] is not None else None
    }

@app.get("/requests/{request_id}")
async def get_request(request_id: str):
    conn = await get_conn()
    cur = await conn.cursor()

    await cur.execute("""
        SELECT request_id, model, prompt_hash, start_ts, end_ts, latency_ms, tokens
        FROM requests WHERE request_id=%s
    """, (request_id,))
    req = await cur.fetchone()

    if not req:
        await cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="request not found")

    await cur.execute("""
        SELECT ts, raw_line FROM events_raw
        WHERE request_id=%s ORDER BY id ASC
    """, (request_id,))
    events = await cur.fetchall()

    await cur.close()
    conn.close()

    return {
        "summary": {
            "request_id": req[0],
            "model": req[1],
            "prompt_hash": req[2],
            "start_ts": req[3],
            "end_ts": req[4],
            "latency_ms": req[5],
            "tokens": req[6]
        },
        "events": [{"ts": e[0], "raw_line": e[1]} for e in events]
    }



# Version 109 changes
@app.get("/proxy/{agent}/conversations")
async def list_conversations(agent: str = Path(...), limit: int = Query(100), offset: int = Query(0)):
    path = get_action_path(agent, "data_list")
    upstream = compose_upstream(agent, path)

    # Log upstream call
    logger.info("Proxying list_conversations agent=%s upstream=%s params=%s", agent, upstream, {"limit": limit, "offset": offset})

    async with httpx.AsyncClient() as client:
        resp = await client.get(upstream, params={"limit": limit, "offset": offset})

    # Log upstream response summary
    try:
        content_preview = (resp.text[:500] + "...") if len(resp.text) > 500 else resp.text
    except Exception:
        content_preview = "<unable to read response text>"
    logger.info("Upstream response for list_conversations agent=%s status=%s content_len=%d preview=%s",
                agent, resp.status_code, len(resp.content or b""), content_preview)

    try:
        content = resp.json()
    except Exception:
        content = resp.text
    return JSONResponse(status_code=resp.status_code, content=content)


@app.get("/proxy/{agent}/conversations/{conversation_title}/messages")
async def get_messages(
    agent: str = Path(...),
    conversation_title: str = Path(...),
    limit: int = Query(200),
    offset: int = Query(0)
):
    path = get_action_path(agent, "data_messages")
    upstream = compose_upstream(agent, path)

    # Log upstream call
    logger.info("Proxying get_messages agent=%s upstream=%s params=%s",
                agent, upstream, {"conversation_title": conversation_title, "limit": limit, "offset": offset})

    async with httpx.AsyncClient() as client:
        resp = await client.get(upstream, params={"conversation_title": conversation_title, "limit": limit, "offset": offset})

    # Log upstream response summary
    try:
        content_preview = (resp.text[:500] + "...") if len(resp.text) > 500 else resp.text
    except Exception:
        content_preview = "<unable to read response text>"
    logger.info("Upstream response for get_messages agent=%s status=%s content_len=%d preview=%s",
                agent, resp.status_code, len(resp.content or b""), content_preview)

    try:
        content = resp.json()
    except Exception:
        content = resp.text
    return JSONResponse(status_code=resp.status_code, content=content)


@app.delete("/proxy/{agent}/conversations/{conversation_title}")
async def delete_conversation(agent: str = Path(...), conversation_title: str = Path(...)):
    path = get_action_path(agent, "delete")
    upstream = compose_upstream(agent, path)

    # Log upstream call
    logger.info("Proxying delete_conversation agent=%s upstream=%s params=%s",
                agent, upstream, {"conversation_title": conversation_title})

    async with httpx.AsyncClient() as client:
        resp = await client.delete(upstream, params={"conversation_title": conversation_title})

    # Log upstream response summary
    try:
        content_preview = (resp.text[:500] + "...") if len(resp.text) > 500 else resp.text
    except Exception:
        content_preview = "<unable to read response text>"
    logger.info("Upstream response for delete_conversation agent=%s status=%s content_len=%d preview=%s",
                agent, resp.status_code, len(resp.content or b""), content_preview)

    try:
        content = resp.json()
    except Exception:
        content = resp.text
    return JSONResponse(status_code=resp.status_code, content=content)

@app.get("/analytics/summaries/{conversation_title}") #version 114
async def analytics_summaries_by_title(conversation_title: str, limit: int = 50):
    """
    Return summaries for a specific conversation_title.
    Used by UI analytics and debugging tools.
    """

    try:
        conn = await get_conn()
        cur = await conn.cursor()

        await cur.execute("""
            SELECT s.id, s.prompt_id, s.user_intent, s.llm_summary, s.created_at,
                   p.conversation_title
            FROM summaries s
            JOIN prompts p ON s.prompt_id = p.id
            WHERE p.conversation_title = %s
            ORDER BY s.created_at DESC
            LIMIT %s
        """, (conversation_title, limit))

        rows = await cur.fetchall()
        await cur.close()
        conn.close()

    except Exception as e:
        logger.error(f"Analytics summary DB error for conversation_title={conversation_title}: {repr(e)}")
        raise HTTPException(status_code=500, detail="analytics summary db error")

    return {
        "conversation_title": conversation_title,
        "summaries": [
            {
                "id": r[0],
                "prompt_id": r[1],
                "user_intent": r[2],
                "llm_summary": r[3],
                "created_at": r[4],
                "conversation_title": r[5]
            }
            for r in rows
        ]
    }


async def run_summary(prompt, llm_response, req_id, conversation_title, model, prompt_id):  # Version 114
    """
    Generate a short summary using Qwen agent.
    Returns dict or None.
    """
    import json
    import re
    import asyncio
    import httpx

    # 0) sanitize inputs to avoid control chars that break JSON
    def sanitize_for_json(s: str) -> str:
        if s is None:
            return ""
        s = str(s)
        return re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', '', s)

    prompt = sanitize_for_json(prompt)
    llm_response = sanitize_for_json(llm_response)

    # 1) Älä yritä summarya jos ei ole mitään tiivistettävää
    if not llm_response or not str(llm_response).strip():
        logger.info(f"No llm_response to summarize for req_id={req_id} conversation_title={conversation_title}")
        return None

    # 2) Rakenna summary payload (sisältö säilyy ennallaan)
    summary_payload = {
        "task": {
            "instruction": (
                "Generate two summaries: (1) user_intent: summarize the user's question in max 10 words. "
                "(2) llm_summary: summarize the model's answer in max 10 words. "
                "Do not repeat or quote the input."
            )
        },
        "input": {
            "user_prompt": prompt,
            "llm_response": llm_response
        },
        "meta": {
            "req_id": req_id,
            "conversation_title": conversation_title,
            "model": model,
            "notes": "Separate intent and semantic summaries to avoid echoing."
        }
    }

    try:
        # Build a human-readable instruction block + JSON code block (exactly this form goes to agent)
        human_instructions = (
            "Summarise the content inside the code block.\n"
            "Produce ONLY the following fields:\n"
            "user_intent: a short summary (max 10 words) of the user's question\n"
            "llm_summary: a short summary (max 10 words) of the model's answer\n"
            "Do not repeat the input.\n"
            "Do not reconstruct the input structure.\n"
            "Do not include any other fields.\n"
            "Do not echo the code block.\n"
            "Output must be valid JSON with exactly these two fields.\n"
        )

        # inner_json is the JSON data the user wants summarized (kept as JSON text inside the code fence)
        inner_json = json.dumps(summary_payload, ensure_ascii=False)

        # Compose the prompt as: human instructions + ```json\n<inner_json>\n```
        composed_prompt = human_instructions + "\n```json\n" + inner_json + "\n```"

        post_body = {
            # IMPORTANT: send composed_prompt as a string in top-level prompt
            "prompt": composed_prompt,
            "stream": False,
            "model": model,
            "conversation_title": conversation_title,
            "req_id": req_id
        }

        # Pieni preview lokiin (ei koko payloadia jos iso)
        try:
            preview = post_body["prompt"][:1000]
        except Exception:
            preview = "<could not preview prompt>"

        logger.info(f"run_summary sending to upstream req_id={req_id} prompt_preview={preview!r} model={model}")

        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(AGENT_URLS["ollama-qwen"] + "/generate", json=post_body)

        # 4) Loggaa upstreamin vastaus (rajoitettu preview)
        try:
            resp_text = resp.text
        except Exception:
            resp_text = (await resp.aread()).decode(errors="replace")

        logger.info(f"run_summary upstream status={resp.status_code} req_id={req_id} body_preview={resp_text[:2000]!r}")

        if resp.status_code >= 400:
            logger.error(f"Summary upstream error {resp.status_code} for req_id={req_id}")
            return None

        # 5) Parsitaan JSON‑vastaus
        try:
            data = resp.json()
        except Exception as e:
            logger.error(f"Summary parse error (top-level json): {repr(e)} resp_text_preview={resp_text[:2000]!r}")
            return None

        # data voi olla:
        # 1) suora dict: {"user_intent": "...", "llm_summary": "..."}
        # 2) dict jossa text on JSON-string: {"request_id": "...", "text": "```json\n{...}\n```", ...}
        user_intent = None
        llm_summary = None

        # 1) suora tapaus
        if isinstance(data, dict) and "user_intent" in data and "llm_summary" in data:
            user_intent = data.get("user_intent")
            llm_summary = data.get("llm_summary")
        else:
            # 2) yritetään purkaa data["text"] jos sellainen on
            text_field = None
            if isinstance(data, dict) and "text" in data:
                text_field = data.get("text")

            if text_field:
                # Poista mahdolliset markdown code fences kuten ```json ... ```
                try:
                    # remove leading/trailing whitespace and fences
                    tf = str(text_field).strip()
                    # strip triple backticks and optional language tag
                    tf = re.sub(r'^```(?:json|json\n)?', '', tf, flags=re.IGNORECASE)
                    tf = re.sub(r'```$', '', tf, flags=re.IGNORECASE)
                    tf = tf.strip()
                    # yritä json.loads
                    parsed = None
                    try:
                        parsed = json.loads(tf)
                    except Exception:
                        # jos ei suoraan, yritä unescape ja uudelleen
                        try:
                            unescaped = tf.encode('utf-8').decode('unicode_escape')
                            parsed = json.loads(unescaped)
                        except Exception:
                            parsed = None

                    if isinstance(parsed, dict):
                        user_intent = parsed.get("user_intent")
                        llm_summary = parsed.get("llm_summary")
                    else:
                        # heuristinen regex fallback
                        m1 = re.search(r'"user_intent"\s*:\s*"([^"]{1,500})"', tf)
                        m2 = re.search(r'"llm_summary"\s*:\s*"([^"]{1,500})"', tf)
                        if m1:
                            user_intent = m1.group(1)
                        if m2:
                            llm_summary = m2.group(1)
                except Exception:
                    pass

        # Lopullinen validointi
        if not user_intent or not llm_summary:
            logger.error(f"Summary JSON missing required fields after parsing. top_level_keys={list(data.keys())} parsed_user_intent={bool(user_intent)} parsed_llm_summary={bool(llm_summary)} resp_preview={resp_text[:2000]!r}")
            return None

        # 6) Tallenna summary proxyn kantaan viitaten paikalliseen prompt_id:hen
        try:
            conn = await get_conn()
            cur = await conn.cursor()
            await cur.execute(
                """
                INSERT INTO summaries (prompt_id, user_intent, llm_summary)
                VALUES (%s, %s, %s)
                """,
                (prompt_id, user_intent, llm_summary)
            )
            await conn.commit()
            await cur.close()
            conn.close()
            logger.info(f"Saved summary for prompt_id={prompt_id} req_id={req_id}")
        except Exception as db_e:
            logger.error(f"Failed to save summary for prompt_id={prompt_id}: {repr(db_e)}")
            return {"user_intent": user_intent, "llm_summary": llm_summary}

        return {"user_intent": user_intent, "llm_summary": llm_summary}

    except asyncio.TimeoutError:
        logger.error("Summary generation timed out (180s)")
        return None

    except Exception as e:
        logger.error(f"Summary generation failed: {repr(e)}")
        return None

async def build_summary_chain(conversation_title): #Version 114
    """
    Build a 3‑item summary chain for continuing conversations.
    Returns empty string if no summaries exist.
    """

    try:
        conn = await get_conn()
        cur = await conn.cursor()

        await cur.execute("""
            SELECT s.user_intent, s.llm_summary
            FROM summaries s
            JOIN prompts p ON s.prompt_id = p.id
            WHERE p.conversation_title = %s
            ORDER BY s.created_at DESC
            LIMIT 3
        """, (conversation_title,))

        rows = await cur.fetchall()
        await cur.close()
        conn.close()

    except Exception as e:
        logger.error(f"Summary chain DB error for conversation_title={conversation_title}: {repr(e)}")
        return ""   # fail silently → no context

    # No summaries yet → new conversation
    if not rows:
        logger.info(f"No summaries found for conversation_title={conversation_title}")
        return ""

    parts = []
    for idx, (intent, summary) in enumerate(rows, start=1):
        # Defensive checks
        if not intent or not summary:
            logger.warning(
                f"Summary row missing fields for conversation_title={conversation_title}: "
                f"user_intent={intent}, llm_summary={summary}"
            )
            continue

        parts.append(
            f"{idx}. User intent: {intent}\n"
            f"   Assistant summary: {summary}\n"
        )

    if not parts:
        logger.warning(f"Summary chain built no valid parts for conversation_title={conversation_title}")
        return ""

    chain = (
        "Here is a short summary of the previous conversation:\n\n"
        + "\n".join(parts)
        + "\n"
    )

    logger.info(
        f"Summary chain built for conversation_title={conversation_title}: "
        f"{len(parts)} items"
    )

    return chain



# Tallennus kun UI lähettää promptin (vain tästä eteenpäin tulevat)
async def save_prompt_local(conversation_title: str, prompt_text: str, model: str): #Version 114
    try:
        conn = await get_conn()
        cur = await conn.cursor()
        await cur.execute(
            "INSERT INTO prompts (upstream_id, model, prompt_text, conversation_title) VALUES (NULL, %s, %s, %s)",
            (model, prompt_text, conversation_title)
        )
        await conn.commit()
        local_id = cur.lastrowid
        await cur.close()
        conn.close()
        logger.info(f"Saved local prompt id={local_id} conversation_title={conversation_title}")
        return local_id
    except Exception as e:
        logger.error(f"Failed to save local prompt conversation_title={conversation_title}: {repr(e)}")
        return None

# Päivitys kun agentin vastaus saapuu
async def update_prompt_local(local_prompt_id: int, upstream_id: str, response_text: str): #Version 114
    if not local_prompt_id:
        return
    try:
        conn = await get_conn()
        cur = await conn.cursor()
        await cur.execute(
            "UPDATE prompts SET upstream_id=%s, response_text=%s WHERE id=%s",
            (upstream_id, response_text, local_prompt_id)
        )
        await conn.commit()
        await cur.close()
        conn.close()
        logger.info(f"Updated local prompt id={local_prompt_id} upstream_id={upstream_id}")
    except Exception as e:
        logger.error(f"Failed to update local prompt id={local_prompt_id}: {repr(e)}")