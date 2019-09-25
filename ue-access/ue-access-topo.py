#!/usr/bin/python

"""
UE Access Component Skeleton

       [Controller c0]

[Switch s1-1] - [Switch s1-2]
      |       X       |
[Switch s2-1] - [Switch s2-2]
   V          V          V
[UE h0]    [UE h1]    [UE h2]

"""

from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.log import setLogLevel, info
from mininet.cli import CLI
from mininet.topo import Topo

import mininet.ns3
from mininet.ns3 import SimpleLink


class UEAcessTopo(Topo):
    "Topology of UE Access Component"

    def __init__(self, **kwargs):
        Topo.__init__(self, **kwargs)
        
        # Declare Switches and Hosts
        switches = [
            self.addSwitch('ue-s1-1'),
            self.addSwitch('ue-s1-2'),
            self.addSwitch('ue-s2-1'),
            self.addSwitch('ue-s2-2')
        ]
        hosts = [
            self.addHost('h0', ip='10.0.0.1'),
            self.addHost('h1', ip='10.0.0.2'),
            self.addHost('h2', ip='10.0.0.3')
        ]

        # Add Link Between Switches
        for i in range(3):
            for j in range(i + 1, 4):
                self.addLink(switches[i], switches[j])

        # Add Link Between s2-1, s2-2 Switch and Hosts
        for i in range(2, 4):
            for host in hosts:
                self.addLink(switches[i], host)

if __name__ == "__main__":
    setLogLevel('info')

    topo = UEAcessTopo()
    ctrl = RemoteController('ue-c0', ip="127.0.0.1", port=6633)
    net = Mininet(topo=topo, controller=ctrl)

    info('*** Connecting NS3 Simple Link\n')
    for i in range(2, 4):
        for j in range(3):
            SimpleLink(net.switches[i], net.hosts[j])

    info('*** Starting UE Access Component network\n')
    net.start()
    mininet.ns3.start()

    info('*** Running CLI\n')
    CLI(net)

    info('*** Stopping network')
    mininet.ns3.clear()
    net.stop()
