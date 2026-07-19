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


