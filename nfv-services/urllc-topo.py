#!/usr/bin/python

"""
NFV Services Management Component Skeleton
(URLLC)

[Controller c0]
       |
  [Switch s0]

"""

from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.log import setLogLevel, info
from mininet.cli import CLI

import mininet.ns3
from mininet.ns3 import SimpleLink

from _topo import NFVServiceTopo

if __name__ == "__main__":
    setLogLevel('info')

    topo = NFVServiceTopo('urllc')
    ctrl = RemoteController('nfv-urllc-c0', ip="127.0.0.1", port=6633)
    net = Mininet(topo=topo, controller=ctrl)

    info('*** Connecting NS3 Simple Link\n')

    info('*** Starting UE Access Component network\n')
    net.start()
    mininet.ns3.start()

    info('*** Running CLI\n')
    CLI(net)

    info('*** Stopping network')
    mininet.ns3.clear()
    net.stop()
