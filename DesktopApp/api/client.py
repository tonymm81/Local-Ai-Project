# api/client.py
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from .endpoints import generate_url, list_conversations_url, get_messages_url, delete_conversation_url, stats_url, request_details_url
import os

DEFAULT_TIMEOUT = 620  # sekunteina

class ApiClient:
    def __init__(self, timeout=DEFAULT_TIMEOUT):
        self.timeout = timeout
        s = requests.Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 502, 503, 504])
        s.mount("http://", HTTPAdapter(max_retries=retries))
        s.mount("https://", HTTPAdapter(max_retries=retries))
        self.session = s

    def _attempt_reset(self):# version 112 update. Lets reset agents automaticly, if time out is triggering
        """
        Lähettää reset POSTin API_URL:iin. Käytetään automaattisesti
        generate()-virhetilanteissa (timeout, 5xx yms.).
        Tämä ei nosta poikkeuksia eteenpäin, vain kirjaa mahdolliset virheet.
        """
        try:
            api_url = os.getenv("API_URL", "http://192.168.68.204:5001/admin/reset")
            api_key = os.getenv("API_KEY", "ThisIsThePassw0rd!")  # tyhjä jos ei asetettu
            headers = {"x-api-key": api_key} if api_key else {}
            # lyhyt timeout resetille, älä jää odottamaan liian pitkään
            r = requests.post(api_url, headers=headers, timeout=10)
            try:
                body = r.text
            except Exception:
                body = "<no body>"
            print(f"DEBUG: attempted reset -> status {r.status_code}, body: {body}")
        except Exception as exc:
            print(f"DEBUG: reset attempt failed: {exc}")


    def generate(self, agent: str, prompt: str, model: str, conversation_title: str, user_id: str = None,):
        url = generate_url()
        payload = {
            "agent": agent,
            "action": "generate",
            "prompt": prompt,
            "model": model,
            "conversation_title": conversation_title
        }
        if user_id:
            payload["user_id"] = user_id

        try:
            resp = self.session.post(url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            print("DEBUG PROXY RESPONSE:", data)
            self.last_request_id = data.get("request_id")
            return data
        except requests.exceptions.RequestException as req_exc: # Adding the automatic reset, if post failed in version 112
            # Kun pyyntö epäonnistuu (timeout, 502, 503, 504, yms.), yritetään automaattinen reset
            print(f"DEBUG: generate request failed: {req_exc}; attempting automatic reset.")
            try:
                self._attempt_reset()
            except Exception:
                pass
            # Heitetään alkuperäinen poikkeus eteenpäin kutsujalle
            raise
    
    def list_conversations(self, agent: str, limit: int = 100, offset: int = 0):
        url = list_conversations_url(agent, limit, offset)
        resp = self.session.get(url, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def get_messages(self, agent: str, conversation_title: str, limit: int = 200, offset: int = 0):
        """
        Yrittää ensin percent-enkoodausta (%20). Jos viestit ovat tyhjiä,
        yrittää plus-enkoodausta (hello+again). Palauttaa JSON-dictin.
        """
        from urllib.parse import quote, quote_plus

        # PROXY_BASE: yritä hakea endpointsista, muuten käytä kovakoodattua oletusta
        try:
            from .endpoints import PROXY_BASE
        except Exception:
            PROXY_BASE = "http://192.168.68.204:8080"

        # 1) percent (%20)
        title_pct = quote(conversation_title, safe='')
        url_pct = f"{PROXY_BASE}/proxy/{agent}/conversations/{title_pct}/messages?limit={limit}&offset={offset}"
        try:
            resp = self.session.get(url_pct, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            data = {"conversation_title": conversation_title, "messages": []}

        if data.get("messages"):
            # löytyi viestejä percent-enkoodauksella
            return data

        # 2) fallback: plus-enkoodaus (hello+again)
        title_plus = quote_plus(conversation_title)
        url_plus = f"{PROXY_BASE}/proxy/{agent}/conversations/{title_plus}/messages?limit={limit}&offset={offset}"
        try:
            resp2 = self.session.get(url_plus, timeout=self.timeout)
            resp2.raise_for_status()
            data2 = resp2.json()
        except Exception:
            data2 = {"conversation_title": conversation_title, "messages": []}

        return data2



    def delete_conversation(self, agent: str, conversation_title: str):
        url = delete_conversation_url(agent, conversation_title)
        resp = self.session.delete(url, timeout=self.timeout)
        resp.raise_for_status()
        return resp.status_code == 200


    def get_stats(self):
        url = stats_url()
        resp = self.session.get(url, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def get_request_details(self, request_id: str):
        url = request_details_url(request_id)
        resp = self.session.get(url, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()