# current_agent_store.py
from typing import List, Optional
from data.models import Message, AgentData
from data.server_repo import ServerRepository

class CurrentAgentStore:
    def __init__(self, repo: ServerRepository):
        self.repo = repo
        self.agent_id: Optional[str] = None
        self.agent_data: Optional[AgentData] = None
        # cache: topic -> list[Message] (vain aktiiviselle agentille)
        self.messages_cache: dict[str, List[Message]] = {}

    def load_agent(self, agent_id: str) -> AgentData:
        """Valitse agentti: tyhjennä vanha cache ja lataa agentin metadata (topics)."""
        self.clear()
        self.agent_id = agent_id
        self.agent_data = self.repo.load_agent(agent_id)
        return self.agent_data

    def clear(self):
        """Tyhjennä paikallinen cache (kutsutaan agentin vaihdossa)."""
        self.agent_id = None
        self.agent_data = None
        self.messages_cache.clear()

    def get_topics(self) -> List[str]:
        return self.agent_data.topics if self.agent_data else []

    def load_messages_for_topic(self, topic: str) -> List[Message]:
        if not self.agent_id:
            raise RuntimeError("No agent selected")
        resp = self.repo.get_messages(self.agent_id, topic)
        print("DEBUG: load_messages_for_topic raw:", resp)

        items = []
        if isinstance(resp, dict):
            items = resp.get("messages") or resp.get("items") or []
        elif isinstance(resp, list):
            items = resp

        msgs = []
        for it in items:
            if not isinstance(it, dict):
                m = Message(content=str(it), conversation_title=topic)
                msgs.append(m)
                continue

            # Etsi kentät useista nimistä
            prompt_text = it.get("prompt_text") or it.get("user") or it.get("input") or it.get("message") or None
            response_text = it.get("response_text") or it.get("assistant") or it.get("response") or it.get("text") or it.get("content") or None

            # Jos vain assistant löytyy, yritä etsiä edellistä user‑viestiä (jos API palauttaa kronologian)
            m = Message(
                id=it.get("id"),
                role=it.get("role"),
                model=it.get("model"),
                prompt_text=prompt_text,
                response_text=response_text,
                conversation_id=it.get("conversation_id"),
                conversation_title=topic,
                created_at=it.get("created_at"),
                content=(response_text or prompt_text or it.get("content") or "")
            )
            msgs.append(m)

        self.messages_cache[topic] = msgs
        return msgs


    def append_message(self, topic: str, prompt: str, response: str, model: str, conversation_id: Optional[str]=None) -> Message:
        """Lisää viestin paikalliseen cacheen (ja UI voi näyttää sen). Palauttaa Message-olion.
           Tallennus palvelimelle tehdään erikseen generate()-kutsussa tai repo.save_prompt jos halutaan."""
        m = Message(id=None, model=model, prompt_text=prompt, response_text=response,
                    conversation_id=conversation_id, conversation_title=topic)
        self.messages_cache.setdefault(topic, []).append(m)
        return m

    def save_prompt_to_server(self, topic: str, prompt: str, model: str, user_id: Optional[str]=None):
        """Synkroninen kutsu palvelimelle: generate -> tallentaa ja palauttaa serverin vastauksen (dict)."""
        if not self.agent_id:
            raise RuntimeError("No agent selected")
        result = self.repo.generate(agent_id=self.agent_id, prompt=prompt, model=model, conversation_title=topic, user_id=user_id)
        self.repo.api.last_request_id = result.get("request_id")#version 111
        # result voi sisältää tallennetun promptin id, response, created_at jne.
        # Päivitä cache: lisää uusi Message, käytä result:n kenttiä jos saat
        response_text = result.get("response") or result.get("text") or str(result)
        conversation_id = result.get("conversation_id") or None
        created_at = result.get("created_at") or None
        msg = Message(id=result.get("id"), model=model, prompt_text=prompt, response_text=response_text,
                      conversation_id=conversation_id, conversation_title=topic, created_at=created_at)
        self.messages_cache.setdefault(topic, []).append(msg)
        return msg

    def delete_conversation(self, topic: str) -> bool:
        if not self.agent_id:
            raise RuntimeError("No agent selected")
        print("DEBUG: CurrentAgentStore.delete_conversation calling repo for topic:", topic)
        ok = self.repo.delete_conversation(self.agent_id, topic)
        print("DEBUG: repo.delete_conversation returned raw:", ok)
        # jatka kuten ennen
        if ok:
            self.messages_cache.pop(topic, None)
            self.agent_data = self.repo.load_agent(self.agent_id)
        return bool(ok)
