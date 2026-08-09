# api/endpoints.py
from urllib.parse import quote_plus
from urllib.parse import quote

# Muuta base_url oikeaksi proxyn osoitteeksi
BASE_URL = "http://192.168.68.204:8080"

def generate_url():
    return f"{BASE_URL}/generate"

def list_conversations_url(agent: str, limit: int = 100, offset: int = 0):
    return f"{BASE_URL}/proxy/{agent}/conversations?limit={limit}&offset={offset}"

def get_messages_url(agent: str, conversation_title: str, limit: int = 200, offset: int = 0):
    title_enc = quote_plus(conversation_title)
    return f"{BASE_URL}/proxy/{agent}/conversations/{title_enc}/messages?limit={limit}&offset={offset}"

def delete_conversation_url(agent: str, conversation_title: str):
    title_enc = quote_plus(conversation_title)
    return f"{BASE_URL}/proxy/{agent}/conversations/{title_enc}"

def stats_url(): # version 111 adding the analytics
    return f"{BASE_URL}/stats"

def request_details_url(request_id: str):
    return f"{BASE_URL}/requests/{request_id}"