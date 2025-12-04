## Local host ai project

- I build the linux server from my old gaming laptop. Then I download the ollama deepseek to there and it is running inside docker container. There is also ollama_watchdog.py what is controlling, that how long time ai agent can convert the answer.

- There is also ollama_proxy, what handles the api calls from client applications. Ollama agent answers like one word per apirequest so this ollama_proxy collect the ai agent answer before restore it to client application.

- Goal of this project is inspect, how ai actually work. I have build the analytics data base to linux server

### Version 100

- Agent is cvommunicating to me now trough api requestes and next step is to build up the phone application and desktop application. I build the analytics around the ai agent, so that data also is needed to handle some how.

### Version 101
- I am trying to make reset ai server service, that sometimes ollama keeps generating like endless loop when it try to generate the responce. There is some problems that I need to figure out

### version 102
- Buildin the desktopapp, where I can communicate to ollama. I also add some text format to tkinter app. But I have issue. Sometimes olamas answer generating is freezing the linux server, so I have to figure out, what is causing this? The broken linux system files of gpu driver?

## Test
- curl -s -X POST http://127.0.0.1:8080/generate \
  -H "Content-Type: application/json" \
  -d '{"model":"pixtral-12b-q2:latest","prompt":"test","max_tokens":32}' | jq .

### Ssh connection test postman

- http://127.0.0.1:9000/generate and 
{
  "model": "pixtral-12b-q2:latest",
  "prompt": "test",
  "max_tokens": 32
}

## ai project folder path


mnt/tonidata/AgentOllamaDeepseek/agent/  |-.env             /models/
                                         |- Dockerfile
                                         |- main.py
                                         |- requirements.txt
mnt/tonidata/AgentOllamaDeepseek/backups/

mnt/tonidata/AgentOllamaDeepseek/compose/ |- .env               /.venv/
                                          |- Docker-compose.yml


mnt/tonidata/AgentOllamaDeepseek/mariadb_data/

mnt/tonidata/AgentOllamaDeepseek/ollama_data/models/ | /blobs/
                                                     | /manifests/| ||||||registry.ollama.ai/library/pixtral-12b-q2

usr/bin/ollama_watchdog.py

/opt/ollama_proxy
├─ main.py // in repo Ollama_Proxy_main.py
|-Ollama_Proxy_ndjsonparser.py
├─ requirements.txt
├─ venv/            # virtuaaliympäristö
/var/lib/ollama_analytics
└─ analytics.db
/var/log/ollama_proxy
└─ out.log
└─ err.log
/etc/systemd/system/ollama-proxy.service

/usr/local/bin/reset_agent.sh

/opt/admin_reset/ admin_reset.py

### Reset in server
- sudo bash -x /usr/local/bin/reset_agent.sh 2>&1 | sudo tee /var/log/reset_agent.log

- curl -v -X POST http://127.0.0.1:5001/admin/reset -H "x-api-key: Sencured"

- ssh -p 9000 -L 5001:127.0.0.1:8080 tonymm81@192.168.68.126 -N

- Ollama 8080 ja resetointipalveli 5001

## Python venv

- python -m venv .venv

- source .venv/Scripts/activate

- python -m pip install requests

- ./.venv/Scripts/python.exe app.py


