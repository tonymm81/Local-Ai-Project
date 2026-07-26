# scripts/test_repo.py
from api.client import ApiClient
from data.server_repo import ServerRepository
from current_agent_store import CurrentAgentStore

api = ApiClient(timeout=10)
repo = ServerRepository(api)   # agent_keys ei pakollinen
store = CurrentAgentStore(repo)

AGENT = "ollama-qwen"   # testaa kullakin agentilla

# 1) lataa agent metadata (topics)
agent_data = store.load_agent(AGENT)
print("AgentData:", agent_data)

# 2) listaa topicit
print("Topics:", store.get_topics())

# 3) hae viestejä yhdestä topicista (jos löytyy)
if store.get_topics():
    t = store.get_topics()[0]
    msgs = store.load_messages_for_topic(t)
    print("Messages for", t, "count:", len(msgs))
else:
    print("No topics to test messages with")

# 4) testaa generate (varovasti, voi luoda uutta)
# resp = store.save_prompt_to_server("TestTopic", "Hello test", "qwen2.5:7b", user_id="tester")
# print("Generate resp:", resp)
