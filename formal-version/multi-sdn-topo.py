#!/usr/bin/python

from mininet.net import Mininet
from mininet.node import OVSSwitch, RemoteController, OVSBridge
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import setLogLevel, info

import mininet.ns3
from mininet.ns3 import SimpleLink

controllers = {}
switches = {}
hosts = {}


def DistrubutedSBANet():
    "initialize network"
    info('-----------------------------------------\n')
    info('| Distributed SDN-based 5G Core Network |\n')
    info('|    Qualcomm Project 2019/6-2019/12    |\n')
    info('|      Yu Chiao Hsu, Han Hsuan Lin      |\n')
    info('-----------------------------------------\n')

    net = Mininet(controller=None, switch=OVSSwitch, link=TCLink, autoSetMacs=True)
    # net = Mininet(controller=None, switch=OVSBridge, link=TCLink)

    ue_access_component(net, 6661)
    nfv_service_component(net, 'URLLC', 6671)
    nfv_service_component(net, 'eMBB', 6681)
    nfv_service_component(net, 'mMTC', 6691)

    # Link UE switch 2-2 to NFV Services' controllers
    net.addLink(switches['ue'][3], switches['n_URLLC'][0])
    net.addLink(switches['ue'][3], switches['n_eMBB'][0])
    net.addLink(switches['ue'][3], switches['n_mMTC'][0])

    return net


def ue_access_component(net, controller_port=6661):
    "add UE Access Component topo"

    # Add controllers, switches and hosts
    info('*** Starting UE Access Controller at {}\n'.format(controller_port))
    controllers['ue'] = net.addController('ue-c0', controller=RemoteController, port=controller_port)
    switches['ue'] = [
        net.addSwitch('ue_s1_1'),
        net.addSwitch('ue_s1_2'),
        net.addSwitch('ue_s2_1'),
        net.addSwitch('ue_s2_2')
    ]
    hosts['ue'] = [
        net.addHost('ue_URLLC_h', ip='10.0.0.71'),
        net.addHost('ue_eMBB_h', ip='10.0.0.81'),
        net.addHost('ue_mMTC_h', ip='10.0.0.91')
    ]
    # Add link between switches
    # for i in range(3):
    #     for j in range(i + 1, 4):
    #         net.addLink(switches['ue'][i], switches['ue'][j])

    for i in range(1, 4):
        net.addLink(switches['ue'][0], switches['ue'][i])

    # Add Link Between s2-1, s2-2 Switch and Hosts
    for i in range(2, 4):
        for host in hosts['ue']:
            net.addLink(switches['ue'][i], host)
            SimpleLink(switches['ue'][i], host)


def nfv_service_component(net, scenario=None, controller_port=6671):
    "add NFV Service Component topo"
    if not scenario:
        info('*** NFV Scenario Missing ***\n')
        return

    # Add controllers, switches and hosts
    COMP_NAME = 'n_{}'.format(scenario)
    info('*** Starting NFV Service-{} Controller at {}\n'.format(scenario, controller_port))
    controllers[COMP_NAME] = net.addController(
        COMP_NAME + '_c0',
        controller=RemoteController,
        port=controller_port
    )
    switches[COMP_NAME] = [
        net.addSwitch(COMP_NAME + '_s0')
    ]
    hosts[COMP_NAME] = [
        net.addHost(COMP_NAME + '_h0'),
    ]

    # Add link between switch and host
    net.addLink(switches[COMP_NAME][0], hosts[COMP_NAME][0])


if __name__ == "__main__":
    setLogLevel('info')

    net = DistrubutedSBANet()

    info('*** Starting Distributed SDN-based 5G Core Network\n')
    net.build()

    for k, c in controllers.items():
        c.start()

    for k, comp in switches.items():
        for switch in comp:
            switch.start([controllers[k]])
            # switch.start([])

    mininet.ns3.start()

    # info('*** Dumping all Controller, Switch and Hosts\n')
    # print controllers
    # print switches
    # print hosts

    # info('*** Testing Hosts')
    # net.pingAll()

    info('*** Running CLI\n')
    CLI(net)

    info('*** Stopping network')
    mininet.ns3.clear()
    net.stop()
