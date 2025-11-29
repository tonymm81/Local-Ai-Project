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
