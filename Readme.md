## Local host ai project

- I build the linux server from my old gaming pc. Then I download the ollama to there and it is running inside docker container. There is also ollama_watchdog.py what is controlling, that how long time ai agent can convert the answer.

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

### version 111
- DeskTopApp is deprecated and not working any more.
- I will merge this branch, because new features is working now and there is only small changes, what needs to be done.
- Repairing the analytics view

##### bug and plans

- Earlier agent answer is staying in agent responce window and it should be removed, when chancing the new agent.
- Perhaps I just add clear conversation history button, what removes the old answers
- Perhaps I need text formatter to agents answer. (the old text formatted did not work so good)
- wholse ui is freezing when it is waiting agent answer and also that why the cancel button wont work.
- When Iam selecting the old conversation, it returns to prompt window but there should be something, what tells to agent that this was the earlier answer.
- Promt input field should be also scroll window like code block is now.


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

Computer specs:
  Host: tonymm81-MS-7680 Kernel: 7.0.0-28-generic arch: x86_64 bits: 64 compiler: gcc v: 13.3.0
    clocksource: tsc
  Console: pty pts/0 DM: LightDM v: 1.30.0 Distro: Linux Mint 22.2 Zara base: Ubuntu 24.04 noble
Machine:
  Type: Desktop Mobo: MSI model: Z87-G45 GAMING (MS-7821) v: 1.0 serial: <superuser required>
    uuid: <superuser required> BIOS: American Megatrends v: 1.9 date: 07/21/2014
CPU:
  Info: quad core model: Intel Core i5-4670K bits: 64 type: MCP smt: <unsupported> arch: Haswell
    rev: 3 cache: L1: 256 KiB L2: 1024 KiB L3: 6 MiB
  Speed (MHz): avg: 928 high: 1315 min/max: 800/3800 cores: 1: 1315 2: 800 3: 800 4: 800
    bogomips: 27197
  Flags: avx avx2 ht lm nx pae sse sse2 sse3 sse4_1 sse4_2 ssse3 vmx
Graphics:
  Device-1: NVIDIA GP104 [GeForce GTX 1070] vendor: ASUSTeK driver: nvidia v: 580.173.02
    arch: Pascal pcie: speed: 2.5 GT/s lanes: 16 ports: active: none empty: DP-1, DP-2, DVI-D-1,
    HDMI-A-1, HDMI-A-2 bus-ID: 01:00.0 chip-ID: 10de:1b81 class-ID: 0300
  Display: server: X.org v: 1.21.1.11 with: Xwayland v: 23.2.6 driver: X: loaded: nvidia
    unloaded: fbdev,modesetting,nouveau,vesa gpu: nvidia tty: 317x85
  API: EGL v: 1.5 hw: drv: nvidia platforms: device: 0 drv: nvidia device: 2 drv: swrast
    surfaceless: drv: nvidia inactive: gbm,wayland,x11,device-1
  API: OpenGL v: 4.6.0 compat-v: 4.5 vendor: mesa v: 25.2.8-0ubuntu0.24.04.2
    note: console (EGL sourced) renderer: NVIDIA GeForce GTX 1070/PCIe/SSE2, llvmpipe (LLVM 20.1.2
    256 bits)
Audio:
  Device-1: Intel 8 Series/C220 Series High Definition Audio vendor: Micro-Star MSI 8
    driver: snd_hda_intel v: kernel bus-ID: 00:1b.0 chip-ID: 8086:8c20 class-ID: 0403
  Device-2: NVIDIA GP104 High Definition Audio vendor: ASUSTeK driver: snd_hda_intel v: kernel
    pcie: speed: 8 GT/s lanes: 16 bus-ID: 01:00.1 chip-ID: 10de:10f0 class-ID: 0403
  API: ALSA v: k7.0.0-28-generic status: kernel-api
  Server-1: PipeWire v: 1.0.5 status: active with: 1: pipewire-pulse status: active
    2: wireplumber status: active 3: pipewire-alsa type: plugin
Network:
  Device-1: Qualcomm Atheros Killer E220x Gigabit Ethernet vendor: Micro-Star MSI driver: alx
    v: kernel pcie: speed: 2.5 GT/s lanes: 1 port: d000 bus-ID: 03:00.0 chip-ID: 1969:e091
    class-ID: 0200
  IF: enp3s0 state: down mac: 44:8a:5b:2b:91:3c
  Device-2: ASUSTek N10 Nano 802.11n Network Adapter [Realtek RTL8192CU] driver: rtl8192cu
    type: USB rev: 2.0 speed: 480 Mb/s lanes: 1 bus-ID: 1-5:2 chip-ID: 0b05:17ba class-ID: 0000
    serial: 00e04c000001
  IF: wlxf832e4b4ddd6 state: up mac: f8:32:e4:b4:dd:d6
  IF-ID-1: br-02dd4899dbd1 state: up speed: 10000 Mbps duplex: unknown mac: ce:22:fc:22:1e:d6
  IF-ID-2: br-2b4be5318cbe state: up speed: 10000 Mbps duplex: unknown mac: 42:8f:7b:b6:45:e1
  IF-ID-3: br-6289f567e166 state: down mac: 6a:c1:f9:b3:81:43
  IF-ID-4: br-ef2ab5352d99 state: up speed: 10000 Mbps duplex: unknown mac: be:8c:bc:bb:2e:4a
  IF-ID-5: br-f5ab522285f8 state: up speed: 10000 Mbps duplex: unknown mac: b6:1b:2a:7d:5e:44
  IF-ID-6: br-f745061caf2d state: down mac: ea:1f:22:4f:68:67
  IF-ID-7: docker0 state: down mac: e6:97:4d:cb:ec:12
  IF-ID-8: veth0b4c33a state: up speed: 10000 Mbps duplex: full mac: 5e:62:19:5f:0d:a0
  IF-ID-9: veth5c0acbd state: up speed: 10000 Mbps duplex: full mac: 4e:61:ce:d9:28:5e
  IF-ID-10: veth826d3ff state: up speed: 10000 Mbps duplex: full mac: da:0e:2e:31:64:7a
  IF-ID-11: veth89c4550 state: up speed: 10000 Mbps duplex: full mac: 8e:eb:71:53:b2:a1
  IF-ID-12: veth8c3861c state: up speed: 10000 Mbps duplex: full mac: 7a:e5:12:06:56:89
  IF-ID-13: vethab4d383 state: up speed: 10000 Mbps duplex: full mac: 72:ab:9b:21:ae:41
  IF-ID-14: vethb048929 state: up speed: 10000 Mbps duplex: full mac: 5a:79:f4:28:86:57
  IF-ID-15: vethf27c208 state: up speed: 10000 Mbps duplex: full mac: ea:2a:4d:4a:3e:bc
Drives:
  Local Storage: total: 909.18 GiB used: 130.43 GiB (14.3%)
  ID-1: /dev/sda vendor: Kingston model: SA400S37240G size: 223.57 GiB speed: 6.0 Gb/s tech: SSD
    serial: 50026B7380D1E56A fw-rev: 0100 scheme: GPT
  ID-2: /dev/sdb vendor: Kingston model: SKC400S37256G size: 238.47 GiB speed: 6.0 Gb/s
    tech: SSD serial: 50026B767600EB68 fw-rev: 001B scheme: GPT
  ID-3: /dev/sdc vendor: Kingston model: SA400S37480G size: 447.13 GiB speed: 6.0 Gb/s tech: SSD
    serial: 50026B77820285C3 fw-rev: 71F1 scheme: GPT
Partition:
  ID-1: / size: 218.51 GiB used: 72.37 GiB (33.1%) fs: ext4 dev: /dev/sda3
  ID-2: /boot/efi size: 512 MiB used: 4 KiB (0.0%) fs: vfat dev: /dev/sda2
Swap:
  ID-1: swap-1 type: file size: 3.82 GiB used: 0 KiB (0.0%) priority: -1 file: /swapfile
Sensors:
  System Temperatures: cpu: 26.0 C mobo: N/A gpu: nvidia temp: 27 C
  Fan Speeds (rpm): N/A
Info:
  Memory: total: 12 GiB available: 11.62 GiB used: 1.22 GiB (10.5%)
  Processes: 234 Power: uptime: 3m states: freeze,mem,disk suspend: deep wakeups: 0
    hibernate: platform Init: systemd v: 255 target: graphical (5) default: graphical
  Packages: pm: dpkg pkgs: 2088 Compilers: gcc: 13.3.0 Shell: Bash v: 5.2.21

