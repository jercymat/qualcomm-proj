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

    # UE Access Component
    ue_access_component(net, 6661)

    # NFV Service Component
    nfv_service_component(net, 'URLLC', 6671)
    nfv_service_component(net, 'eMBB', 6681)
    nfv_service_component(net, 'mMTC', 6691)

    # SBA Entity Component
    sba_entity_component(net, 'sbus', 7001, bus=True)
    sba_entity_component(net, 'NRF', 7011)
    sba_entity_component(net, 'AUSF', 7021)
    sba_entity_component(net, 'UDM', 7031)
    sba_entity_component(net, 'AMF', 7041)
    sba_entity_component(net, 'SMF', 7051)
    sba_entity_component(net, 'PCF', 7061)
    sba_entity_component(net, 'AF', 7071)

    # Link UE switch 1-2 to NFV Services' controllers
    net.addLink(switches['ue'][1], switches['n_URLLC'][0])
    net.addLink(switches['ue'][1], switches['n_eMBB'][0])
    net.addLink(switches['ue'][1], switches['n_mMTC'][0])

    # Link NFV Services to sbus
    net.addLink(switches['n_URLLC'][0], switches['s_sbus'][0])
    net.addLink(switches['n_eMBB'][0], switches['s_sbus'][0])
    net.addLink(switches['n_mMTC'][0], switches['s_sbus'][0])

    # Link SBA Entities to sbus
    net.addLink(switches['s_sbus'][0], switches['s_NRF'][0])
    net.addLink(switches['s_sbus'][0], switches['s_AUSF'][0])
    net.addLink(switches['s_sbus'][0], switches['s_UDM'][0])
    net.addLink(switches['s_sbus'][0], switches['s_AMF'][0])
    net.addLink(switches['s_sbus'][0], switches['s_SMF'][0])
    net.addLink(switches['s_sbus'][0], switches['s_PCF'][0])
    net.addLink(switches['s_sbus'][0], switches['s_AF'][0])

    # info(str(controllers) + '\n')
    # info(str(switches) + '\n')
    # info(str(hosts) + '\n')

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
    for i in range(3):
        for j in range(i + 1, 4):
            net.addLink(switches['ue'][i], switches['ue'][j])

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
    SERV_NAME = 'n_{}'.format(scenario)
    info('*** Starting NFV Service-{} Controller at {}\n'.format(scenario, controller_port))
    controllers[SERV_NAME] = net.addController(
        SERV_NAME + '_c0',
        controller=RemoteController,
        port=controller_port
    )
    switches[SERV_NAME] = [
        net.addSwitch(SERV_NAME + '_s0')
    ]
    hosts[SERV_NAME] = [
        net.addHost(SERV_NAME + '_h0'),
    ]

    # Add link between switch and host
    net.addLink(switches[SERV_NAME][0], hosts[SERV_NAME][0])


def sba_entity_component(net, name=None, controller_port=7011, bus=False):
    "add SBA Entity Component Topo"
    if not name:
        info('*** SBA Entity Name Missing ***\n')
        return

    # Add controllers, switches and hosts
    ENT_NAME = 's_{}'.format(name)
    if not bus:
        info('*** Starting SBA Entity-{} Controller at {}\n'.format(name, controller_port))
    else:
        info('*** Starting SBA BUS Controller at {}\n'.format(controller_port))
    controllers[ENT_NAME] = net.addController(
        ENT_NAME + '_c0',
        controller=RemoteController,
        port=controller_port
    )
    switches[ENT_NAME] = [
        net.addSwitch(ENT_NAME + '_s0')
    ]
    if not bus:
        hosts[ENT_NAME] = [
            net.addHost(ENT_NAME + '_h0'),
        ]

        # Add link between switch and host
        net.addLink(switches[ENT_NAME][0], hosts[ENT_NAME][0])


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
