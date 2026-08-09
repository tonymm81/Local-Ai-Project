# TextFormatter.py
import re
from datetime import datetime
from typing import List, Dict, Tuple

_MAX_PREVIEW = 500

def format_text_for_display(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'\s+([,.;:!?])', r'\1', text)
    text = re.sub(r'\s*"\s*([^"]+?)\s*"\s*', r'"\1"', text)
    text = re.sub(r'([.!?;:])\s+', r'\1\n\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def preview_text(text: str, max_chars: int = _MAX_PREVIEW) -> str:
    if text is None:
        return ""
    text = str(text)
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "..."

def sanitize_conversation_title(title: str, max_len: int = 200) -> str:
    if title is None:
        return ""
    t = title.strip()
    t = re.sub(r'[\r\n]+', ' ', t)
    # Poistetaan kielletyt merkit
    t = re.sub(r'[<>#%{}|\^\[\]`]', '', t)
    if len(t) > max_len:
        t = t[:max_len].strip()
    return t

def _parse_event_raw(raw_line: str) -> Dict:
    try:
        import json
        return json.loads(raw_line)
    except Exception:
        return {"response": raw_line}

def reconstruct_from_events(events: List[Dict], summary: Dict, max_events: int = 10) -> Tuple[str, Dict]:
    parsed_events = []
    reconstructed_parts = []
    for ev in events:
        ts = ev.get("ts")
        raw = ev.get("raw_line", "")
        parsed = _parse_event_raw(raw)
        resp_fragment = ""
        if isinstance(parsed, dict):
            resp_fragment = parsed.get("response") or parsed.get("text") or ""
        else:
            resp_fragment = str(parsed)
        resp_fragment = str(resp_fragment).lstrip()
        parsed_events.append({
            "ts": ts,
            "created_at": parsed.get("created_at") if isinstance(parsed, dict) else None,
            "response": resp_fragment,
            "done": parsed.get("done") if isinstance(parsed, dict) else None,
            "done_reason": parsed.get("done_reason") if isinstance(parsed, dict) else None,
            "raw": raw
        })
        if resp_fragment:
            reconstructed_parts.append(resp_fragment)

    reconstructed_text = " ".join([p.strip() for p in reconstructed_parts if p.strip()])
    reconstructed_text = re.sub(r'\s+([,.;:!?])', r'\1', reconstructed_text)
    reconstructed_text = re.sub(r'\s*"\s*([^"]+?)\s*"\s*', r'"\1"', reconstructed_text)
    reconstructed_text = re.sub(r'\s+', ' ', reconstructed_text).strip()

    start_ts = summary.get('start_ts')
    end_ts = summary.get('end_ts')
    start_iso = None
    end_iso = None
    duration_s = None
    try:
        if start_ts:
            start_iso = datetime.fromtimestamp(float(start_ts)).isoformat(sep=' ')
        if end_ts:
            end_iso = datetime.fromtimestamp(float(end_ts)).isoformat(sep=' ')
        if start_ts and end_ts:
            duration_s = float(end_ts) - float(start_ts)
    except Exception:
        start_iso = start_iso or str(start_ts)
        end_iso = end_iso or str(end_ts)

    analytics = {
        "request_id": summary.get("request_id"),
        "model": summary.get("model"),
        "latency_ms": summary.get("latency_ms"),
        "tokens": summary.get("tokens"),
        "start": start_iso,
        "end": end_iso,
        "duration_s": duration_s,
        "events": parsed_events[-max_events:]
    }

    return reconstructed_text, analytics
