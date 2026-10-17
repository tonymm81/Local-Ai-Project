## reset admin
/usr/local/bin/reset_agent.sh
curl -X POST http://127.0.0.1:5001/admin/reset \
  -H "x-api-key: <sun_api_key>"

## Restart
sudo systemctl restart ollama-proxy.service
sudo systemctl status ollama-proxy.service --no-pager
FragmentPath=/etc/systemd/system/ollama-proxy.service


## Logeja
LOGFILE = "/opt/admin_reset/reset_agent_http.log"

sudo tail -n 50 /opt/admin_reset/reset_agent_http.log
sudo journalctl -u admin_reset.service -n 50 --no-pager
sudo journalctl -u ollama-proxy.service -n 50 --no-pager

## admin_reset
/Opt/admin_reset/admin_reset

sudo journalctl -u ollama-proxy.service -n 200 --no-pager
# proxy main log
sudo tail -n 200 /opt/ollama_proxy/proxy_main.log
sudo tail -f /opt/ollama_proxy/proxy_main.log

# ndjson parser log
sudo tail -n 200 /opt/ollama_proxy/ndJsonParser.log
sudo tail -f /opt/ollama_proxy/ndJsonParser.log

### Linux tricks
nvidia-smi -l 1 tai nvtop
htop

### Reset in server
- sudo bash -x /usr/local/bin/reset_agent.sh 2>&1 | sudo tee /var/log/reset_agent.log

- curl -v -X POST http://127.0.0.1:5001/admin/reset -H "x-api-key: Sencured"

- ssh -p 9000 -L 5001:127.0.0.1:8080 tonymm81@192.168.68.126 -N

- Ollama 8080 ja resetointipalveli 5001

## Python venv for start the client app

- python -m venv .venv

- source .venv/Scripts/activate

- python -m pip install requests

- ./.venv/Scripts/python.exe StartApp.py


### reset proxy server

- sudo cp -f main.py /opt/ollama_proxy/main.py sudo cp -f ndjson_parser.py /opt/ollama_proxy/ndjson_parser.py
- sudo systemctl restart ollama-proxy sudo journalctl -u ollama-proxy -f

### reset all docker containers
- sudo /usr/local/bin/reset_agent.sh

## Proxyn routes updated 12.7.2026
### Qwen:
curl -v -X POST "http://127.0.0.1:8080/generate" \
  -H "Content-Type: application/json" \
  -d '{"agent":"ollama-qwen","action":"generate","prompt":"Hello QWEN, say hi?","model":"qwen2.5:7b","conversation_title":"MyTopic A","user_id":"tester"}'

curl -sS "http://127.0.0.1:8080/proxy/ollama-qwen/conversations?limit=100&offset=0" | jq .
curl -sS "http://127.0.0.1:8080/proxy/ollama-qwen/conversations/MyTopic%20A/messages?limit=200&offset=0" | jq .
curl -v -X DELETE "http://127.0.0.1:8080/proxy/ollama-qwen/conversations/MyTopic%20A"



### dev:

curl -v -X POST "http://127.0.0.1:8080/generate"   -H "Content-Type: application/json"   -d '{"agent":"ollama-dev","action":"generate","prompt":"Hello dev agent, say a full sentence?","model":"phi_2_gguf:latest","conversation_title":"Conversation A"}'

curl -sS "http://127.0.0.1:8080/proxy/ollama-dev/conversations?limit=100&offset=0" | jq .
curl -sS "http://127.0.0.1:8080/proxy/ollama-dev/conversations/Conversation%20A/messages?limit=200&offset=0" | jq .
curl -v -X DELETE "http://127.0.0.1:8080/proxy/ollama-dev/conversations/Conversation%20A"


### Pixatrail 
curl -v -X POST "http://127.0.0.1:8080/generate"   -H "Content-Type: application/json"   -d '{"agent":"pixatrail","action":"generate","prompt":"health check","model":"pixtral-12b-q2:latest","conversation_title":"smoke-test","user_id":"tester"}'

curl -sS "http://127.0.0.1:8080/proxy/pixatrail/conversations?limit=100&offset=0" | jq .
curl -sS "http://127.0.0.1:8080/proxy/pixatrail/conversations/Aamurutiini%3F/messages?limit=200&offset=0" | jq .
curl -v -X DELETE "http://127.0.0.1:8080/proxy/pixatrail/conversations/Aamurutiini%3F"


### summary feature in version 114 testing:

- example body for summarise lmm model answer with qwen:
To clarify:

- **Summary Format**:

Yes, you can receive the summary in JSON format for better organization.

- **Example Response**:

```json
{
    "summary":

[
        "AI project",
        "summarization feature",
        "pixatrail answer",
        "prompt response",
        "keyword extraction",
        "10 keywords",
        "next prompt",
        "project continuation",
        "information organization",
        "JSON format"
    ]
}
```
- This is tested and it work quite good:

Prompt:
summarise the content inside the code block.

Produce ONLY the following fields:

user_intent: a short summary (max 10 words) of the user's question
llm_summary: a short summary (max 10 words) of the model's answer

Do not repeat the input.
Do not reconstruct the input structure.
Do not include any other fields.
Do not echo the code block.
Output must be valid JSON with exactly these two fields.

Json input:
{
  "task": {
    "instruction": "Generate two summaries: (1) user_intent: summarize the user's question in max 10 words. (2) llm_summary: summarize the model's answer in max 10 words. Do not repeat or quote the input."
  },
  "input": {
    "user_prompt": "Miksi TypeScriptin tyypitys on hyödyllistä?",
    "llm_response": "TypeScriptin tyypitys tuo useita konkreettisia etuja kehitykseen..."
  },
  "meta": {
    "req_id": "12345",
    "conversation_title": "typescript_types",
    "model": "qwen2.5",
    "notes": "Separate intent and semantic summaries to avoid echoing."
  }
}
Result Example qwen llm model answer for this:

```json
{
  "user_intent":

"Miksi TypeScriptin tyypitys on hyödyllistä?",
  "llm_summary":

"TypeScriptin tyypitys tarjoaa monia hyötyjä koodin kehityksessä."
}
```

Same prompt but different summarize json:

{
  "task": {
    "instruction": "Generate two summaries: (1) user_intent: summarize the user's question in max 10 words. (2) llm_summary: summarize the model's answer in max 10 words. Do not repeat or quote the input."
  },
  "input": {
    "user_prompt": "What is the practical difference between defining a global TypeScript interface that is available across the entire project versus defining local interfaces inside React components or modules? How do these approaches affect maintainability, type reuse, code clarity, and potential naming conflicts when scaling a large application?",
    "llm_response": "Global TypeScript interfaces provide shared, reusable type definitions that help maintain consistency across the entire codebase, but they can introduce naming collisions and make dependencies less explicit. Local interfaces inside React components or modules improve encapsulation, reduce accidental coupling, and make component boundaries clearer, but they may lead to duplicated types and slightly more boilerplate when multiple components need similar structures."
  },
  "meta": {
    "req_id": "98765",
    "conversation_title": "ts_global_vs_local_interfaces",
    "model": "qwen2.5",
    "notes": "Long-form prompt and answer for summarization testing."
  }
}

- qwen lmm model answer:
{
  "user_intent":

"Difference between global and local TypeScript interfaces.",
  "llm_summary":

"Global interfaces offer reuse, maintain consistency;

locals improve encapsulation, reduce conflicts."
}

Same prompt but different summarize json with lots of special characters:

{
  "task": {
    "instruction": "Generate two summaries: (1) user_intent: summarize the user's question in max 10 words. (2) llm_summary: summarize the model's answer in max 10 words. Do not repeat or quote the input."
  },
  "input": {
    "user_prompt": "What is the practical difference between using global TypeScript interfaces shared across the whole project and defining local, component-specific interfaces inside React files? How do these choices impact reusability, refactoring, naming collisions, and clarity when the codebase grows and different teams touch the same types?",
    "llm_response": "1. Global interfaces:\n   - ✅ Reusable across many modules\n   - ✅ Centralised type definitions\n   - ❌ Higher risk of naming collisions\n   - ❌ Hidden dependencies between components\n\n2. Local interfaces in React components:\n   - ✅ Better encapsulation of component contracts\n   - ✅ Clear, explicit dependencies per file\n   - ✅ Easier to refactor in isolation\n   - ❌ Possible duplication of similar shapes\n\n### Example\n```ts\ninterface GlobalUser {\n  id: string;\n  name: string;\n}\n\ninterface LocalUserProps {\n  user: GlobalUser;\n}\n```\n🚀 In practice: use global interfaces for truly shared domain models, and local interfaces for UI‑specific props and internal structures to keep boundaries clean."
  },
  "meta": {
    "req_id": "ts-echo-stress-001",
    "conversation_title": "ts_global_vs_local_interfaces_stress_test",
    "model": "qwen2.5",
    "notes": "Deliberately messy Ollama-style response with lists, markdown, code and emoji to test echo behaviour."
  }
}
- qwen lmm model answer:
{
  "user_intent":

"Difference between global vs local TypeScript interfaces.",
  "llm_summary":

"Global:

reusable, risk of collisions;

Local:

encapsulated, easier refactoring."
}

### Example summarize database tables:

CREATE TABLE IF NOT EXISTS summaries (
  id INT AUTO_INCREMENT PRIMARY KEY,
  prompt_id INT NOT NULL,
  user_intent VARCHAR(255),
  llm_summary VARCHAR(255),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (prompt_id) REFERENCES prompts(id)
);

- summarised prompt (only 3-5 latest is added to new prompt):

Here is a short summary of the previous conversation:

1. User intent: Asked about TS interfaces
   Assistant summary: Global reusable; local encapsulated

2. User intent: Asked about naming collisions
   Assistant summary: Global types risk collisions; locals avoid them

3. User intent: Asked about refactoring
   Assistant summary: Local types easier to refactor

Now the user asks:
"How should I organize shared types in a large monorepo?"

- This test gives a valid output so we can continue to develop the summarize features to ai project.

### next step to do:

- This test shows that qwen gives the answer without any echo and it also noticed the earlier conversation summary. Now we have to build this feature to proxy server and create new table to mariadb sql. 

- This feature is builded to all llm models.
- We should add logging to summarize feature, becase we cannot 100% trust that ollama qwen ia giving valid json output for proxy server.

- We have to use 3 latest summaries when continuing the conversation. If some of summarys failed, then the conversation is still with history and not broke, because one of summaries has failded.

- We need to clean the existing feature from ui to continue the conversation. Now it use the earlier answer for prompt and we cannnot use it anyway se removing this feature in next version.

- Ui have to wait until llm model is generated the answer and the summarize is complete in local ai server.