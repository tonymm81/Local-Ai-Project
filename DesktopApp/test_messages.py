from api.client import ApiClient
from data.server_repo import ServerRepository

c = ApiClient(timeout=60)
print(c.get_messages("ollama-dev", "hello again"))