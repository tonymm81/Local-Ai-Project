# data/server_repo.py
from typing import Dict, List
from data.models import AgentData, Message
from api.client import ApiClient

class ServerRepository:
    def __init__(self, api_client: ApiClient, agent_keys: list = None):
        self.api = api_client
        self.agent_keys = agent_keys or []

    def load_agent(self, agent_id: str) -> AgentData:
        """Hakee palvelimelta agentin topicit ja palauttaa AgentData (robustimpi parsing)."""
        resp = self.api.list_conversations(agent_id)
        print("DEBUG: load_agent resp raw:", resp)   # poista debug myöhemmin
        titles = []

        if isinstance(resp, dict):
            if "conversations" in resp and isinstance(resp["conversations"], list):
                for c in resp["conversations"]:
                    if isinstance(c, dict):
                        t = c.get("conversation_title") or c.get("title") or c.get("name") or c.get("conversationName")
                        if t:
                            titles.append(t)
                    elif isinstance(c, str):
                        titles.append(c)
            elif "items" in resp and isinstance(resp["items"], list):
                for it in resp["items"]:
                    if isinstance(it, dict):
                        t = it.get("conversation_title") or it.get("title") or it.get("name")
                        if t: titles.append(t)
                    else:
                        titles.append(str(it))
            else:
                for v in resp.values():
                    if isinstance(v, list):
                        for it in v:
                            if isinstance(it, dict):
                                t = it.get("conversation_title") or it.get("title") or it.get("name")
                                if t: titles.append(t)
                            elif isinstance(it, str):
                                titles.append(it)
        elif isinstance(resp, list):
            for item in resp:
                if isinstance(item, dict):
                    t = item.get("conversation_title") or item.get("title") or item.get("name")
                    if t: titles.append(t)
                else:
                    titles.append(str(item))

        # Poista duplikaatit ja tyhjät
        seen = set()
        uniq = []
        for t in titles:
            if t and t not in seen:
                seen.add(t)
                uniq.append(t)

        return AgentData(id=agent_id, display_name=agent_id, default_model=None, topics=uniq)

    def get_messages(self, agent_id: str, conversation_title: str):
        return self.api.get_messages(agent_id, conversation_title)

    def get_messages(self, agent_id: str, conversation_title: str):
        print(f"DEBUG: ServerRepository.get_messages called agent={agent_id!r} title={conversation_title!r}")
        resp = self.api.get_messages(agent_id, conversation_title)
        print("DEBUG: api.get_messages returned:", resp)
        return resp

    def generate(self, agent_id: str, prompt: str, model: str, conversation_title: str, user_id: str = None):
        return self.api.generate(agent=agent_id, prompt=prompt, model=model, conversation_title=conversation_title, user_id=user_id)


    def delete_conversation(self, agent_id: str, conversation_title: str):
        print(f"DEBUG: ServerRepository.delete_conversation called agent={agent_id!r} title={conversation_title!r}")
        resp = self.api.delete_conversation(agent_id, conversation_title)
        print("DEBUG: api.delete_conversation returned:", resp)
        return resp