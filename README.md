# SDN-based Network Slicing Platform of 5G Core Network
An SDN-based solution of Network Slicing in 5G Service Based Architecture (SBA) core network, constructed with multiple SDN subsystems. With full SBA Entities implementation, we can provide network slices of 5G scenarios (URLLC, eMBB, mMTC) for 5G UEs to comsume SBA core network resources.
## Getting Started
### Requirememts
* Ubuntu 14.04↑
* Python 2.7 (2.7.12↑)
### Dependencies
* [Mininet](https://github.com/mininet/mininet) 2.2.1 -> SDN Topology Emulator
* [Ryu](https://github.com/osrg/ryu) 4.32 -> Openflow Controller Framework
* [hyper-h2](https://github.com/python-hyper/hyper-h2) 2.6.2 -> HTTP/2 Server Framework
* [hyper](https://github.com/python-hyper/hyper) 0.7.0 -> HTTP/2 Client Framework
### Installation
Just clone it into your host
```
git clone https://gitlab.com/jercymat/qualcomm-proj.git
```
## Deployment
Clone to your ubuntu host, and make sure that all the dependencies are installed.
1. **Start up Mininet topology**
```
cd qualcomm-proj/formal-version
sudo ./multi-sdn-topo.py
```
2. **Start up Ryu SDN controllers**

There are 12 SDN subsystems constructing the whole system, which means there are 12 Ryu controllers to start.

If you want to run them in background:
```
ryu-manager ue-access-ctrl.py --ofp-tcp-listen-port 6661 --wsapi-port 6662 &

ryu-manager nfv-urllc-ctrl.py --ofp-tcp-listen-port 6671 --wsapi-port 6672 &
ryu-manager nfv-embb-ctrl.py --ofp-tcp-listen-port 6681 --wsapi-port 6682 &
ryu-manager nfv-mmtc-ctrl.py --ofp-tcp-listen-port 6691 --wsapi-port 6692 &

ryu-manager sba-nrf-ctrl.py --ofp-tcp-listen-port 7011 --wsapi-port 7012 &
ryu-manager sba-ausf-ctrl.py --ofp-tcp-listen-port 7021 --wsapi-port 7022 &
ryu-manager sba-udm-ctrl.py --ofp-tcp-listen-port 7031 --wsapi-port 7032 &
ryu-manager sba-amf-ctrl.py --ofp-tcp-listen-port 7041 --wsapi-port 7042 &
ryu-manager sba-smf-ctrl.py --ofp-tcp-listen-port 7051 --wsapi-port 7052 &
ryu-manager sba-pcf-ctrl.py --ofp-tcp-listen-port 7061 --wsapi-port 7062 &
ryu-manager sba-af-ctrl.py --ofp-tcp-listen-port 7071 --wsapi-port 7072 &

ryu-manager dp-upf-ctrl.py --ofp-tcp-listen-port 8001 --wsapi-port 8002 &
```
You can also open a new terminal window for each controller, just type the command above one line per window, but take the trailing `&` off.

It's highly recommended to use [tmux](https://github.com/tmux/tmux).

3. **Start up host servers**

Each subsystem has a server to handle incoming requests, start them in mininet command line:
```
uam_h0 python ./servers/uam_h0.py &

n_URLLC_h0 python ./servers/n_URLLC_h0.py &
n_eMBB_h0 python ./servers/n_eMBB_h0.py &
n_mMTC_h0 python ./servers/n_mMTC_h0.py &

s_NRF_h0 python ./servers/s_NRF_h0.py &
s_AUSF_h0 python ./servers/s_AUSF_h0.py &
s_UDM_h0 python ./servers/s_UDM_h0.py &
s_AMF_h0 python ./servers/s_AMF_h0.py &
s_SMF_h0 python ./servers/s_SMF_h0.py &
s_PCF_h0 python ./servers/s_PCF_h0.py &
s_AF_h0 python ./servers/s_AF_h0.py &

d_UPF_h0 python ./servers/d_UPF_h0.py &
d_DN_h0 python ./servers/d_DN_h0.py &
```
Now your system is ready for sending packets.
## Running
You can now send packets, run the UEs in mininet command line:

**URLLC Scenario**
```
ue_URLLC_h python ./servers/ue_URLLC_h
```
**eMBB Scenario**
```
ue_eMBB_h python ./servers/ue_eMBB_h
```
**mMTC Scenario**
```
ue_mMTC_h python ./servers/ue_mMTC_h
```
Enjoy.
## Declaration
This system is built for Qualcomm Taiwan University Research Program.