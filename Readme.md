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


### version 103
- I have now developed the client app, that it shows the analytics with every responce. I have also developed the server side programs ollama_proxy_main and Ollama_proxy_ndjson_parser.py to return the analytics data.

- app is now working fine and agent responce is showing in Desktopapp, what is different machine. 


### version 104 (adding dev agent)
- I add more disk to computer and it is purpose to use same proxy server with 2 other agents. No I am building the dev agent on ai-aget2 disk. Docker container is up now.
- This agent gets it own database sqlite in agetnt2 disk. This agent is using the same analytics database, that ollama uses.

- This project, I add DevAgent folder, where is this agent files.

### version 105
- Adding agent qwen to this project also. Then we have tree different agent so we have some data, what compare.
- ollama agent qwen is workin now so next step is start to build the communication route all the way to client app

### version 106

- updating the linux components to use 3 different ai agent models. 
- Updating the reset_agent.sh file
- updating the admin_reset.py file logic also.

- Now the admin_reset.py is working as excepted. It reset all the containers and also proxyserver. nest step is to create the routing to post messages from cielnt to ai agent.

- I change the file database to mariadb and it starts to work. When I was testing pixatrail agent, I noticed, that It uses the CPU for generating the answer instead of GPU so I need to give permission to docker container to use gpu in container.

- I noticed, that ollama dev agent does not have own container so it is now updated and agent answers to test curl. 
- Next this is to update ollama-qwen docker-compose.yml file to support GPU using in answer generating.

- And new issue agai and again and again. Proxyserver gives a sql error and nothing helps to it.

### version 107

- Added to client app radio buttons, where user can select, what agent is answering to prompt.
- Added the routes to server in ollama-proxy-server.py and nd_json_parser.py
- Ui updated. Now the agents are responding to python app in client computer. 
- Lets merge the branch for this version


### version 108
- Fixing the reset agent from user ui. Now it is working and it is resetting the containers and proxy service.
- Adding the http post to desktop ui, where user can reset the agents if they stay in endless loop.

#### bug
- the cancelbutton does not do anything, so I think that admin_reset.py has some issues but I need to check the logs, before contiuing troubleshooting. (Fixed on 108)

### version 109
- Planning to add conversation history for this project

#### backend updates
- Agent qwen has now the conversation history feature updated and tested.
- Agent dev has now new conversation feature and it is tested.
- Agent pixatrail has now updated with new features also. This features is tested now.

- Proxy server updated and tested
#### in next version:

- Desktopapp need to plan and update to correct endpoints. 

### version 110

- Added plans, how we should build the user ui app. When this is working, then we create same kind on react native app.

- Created new ui with new logic and routes. I have added the ai agent ui plan.drawio where is graphical user path and logic is explained in ai agent python app ui.txt plan.

- For now ui let user to select existing conversation and pick the answer to continue the conversation.
- Tested with all different agents. Deleting the conversation is also working. Agent response to app.

##### bug and plans

- The analytics window needs to configure ready.
- Earlier agent answer is staying in agent responce window and it should be removed, when chancing the new agent.
- dev agent is not returning any conversation data to ui.

#### plan 01
- Next step is build a react native app for android, that I can send prompts to agent and use it from desktop app and mobile. Of course every returned responces returns also analytics from that sended prompt.

- Also watchdog.py we should consider, that how we get alarm to client app from this.

#### plan 02
- Lets build a feature, that you can see the chat history in client app also.



## ai project pixatrail folder path


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


