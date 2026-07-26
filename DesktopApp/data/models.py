# data/models.py
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Message:
    id: Optional[int] = None
    role: Optional[str] = None            # "user" / "agent"
    content: Optional[str] = None         # fallback: yhdistetty prompt/response tai agentin teksti
    created_at: Optional[str] = None

    # Lisäkentät joita CurrentAgentStore ja repo käyttävät
    model: Optional[str] = None
    prompt_text: Optional[str] = None
    response_text: Optional[str] = None
    conversation_id: Optional[str] = None
    conversation_title: Optional[str] = None

@dataclass
class AgentData:
    id: str                 # esim. "ollama-qwen"
    display_name: str       # esim. "Agent Qwen"
    default_model: Optional[str]
    topics: List[str]
