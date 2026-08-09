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
/Opt/admin_reset/admin_re

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

## Python venv

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


