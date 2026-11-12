# data/server_repo.py
from typing import Dict, List
from data.models import AgentData, Message
from api.client import ApiClient
from common.logger import get_logger

logger = get_logger(__name__)#version 116

class ServerRepository:
    def __init__(self, api_client: ApiClient, agent_keys: list = None):
        self.api = api_client
        self.agent_keys = agent_keys or []

    def load_agent(self, agent_id: str) -> AgentData:
        """Hakee palvelimelta agentin topicit ja palauttaa AgentData (robustimpi parsing)."""
        resp = self.api.list_conversations(agent_id)
        logger.debug(
                    "load_agent raw response=%s",
                    resp
                )  #version 116   # poista debug myöhemmin
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
        logger.info(
        "Loading messages. Agent=%s Topic=%s",
                                            agent_id,
                                            conversation_title
                                                )  #version 116        
        resp = self.api.get_messages(agent_id, conversation_title)
        logger.debug(
                    "get_messages response=%s",
                    resp
                )  #version 116
        return resp

    def generate(self, agent_id: str, prompt: str, model: str, conversation_title: str, user_id: str = None):
        logger.info(
                    "Generating response. Agent=%s Model=%s Topic=%s",
                    agent_id,
                    model,
                    conversation_title
                )  #version 116
        return self.api.generate(agent=agent_id, prompt=prompt, model=model, conversation_title=conversation_title, user_id=user_id)


    def delete_conversation(self, agent_id: str, conversation_title: str):
        logger.info(
                    "Deleting conversation. Agent=%s Topic=%s",
                    agent_id,
                    conversation_title
                )  #version 116
        resp = self.api.delete_conversation(agent_id, conversation_title)
        logger.debug(
                "delete_conversation response=%s",
                resp
            )  #version 116
        return resp

    def get_stats(self):# version 116
        logger.debug(
                    "Loading analytics statistics"
                )  #version 116
        return self.api.get_stats()

    def get_summaries(self, conversation_title: str, limit: int = 50): #version 116
        logger.debug(
                    "Loading summaries. Topic=%s Limit=%s",
                    conversation_title,
                    limit
                )  #version 116
        return self.api.get_summaries(conversation_title, limit)