#!/usr/bin/python

from mininet.net import Mininet
from mininet.node import OVSSwitch, RemoteController
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import setLogLevel, info

# import mininet.ns3
# from mininet.ns3 import SimpleLink
import pprint

controllers = {}
switches = {}
hosts = {}

dpid_cnt = 1


def DistrubutedSBANet():
    "initialize network"
    info('-----------------------------------------\n')
    info('| Distributed SDN-based 5G Core Network |\n')
    info('|    Qualcomm Project 2019/6-2019/12    |\n')
    info('|      Yu Chiao Hsu, Han Hsuan Lin      |\n')
    info('-----------------------------------------\n')

    net = Mininet(controller=None, switch=OVSSwitch,
                  link=TCLink, autoSetMacs=True)

    # UE Access Component
    ue_access_component(net, 6661)

    # NFV Service Component
    nfv_service_component(net, 'URLLC', 6671, 1)
    nfv_service_component(net, 'eMBB', 6681, 2)
    nfv_service_component(net, 'mMTC', 6691, 3)

    # SBA Entity Component
    sba_entity_component(net, 'NRF', 7011, 1)
    sba_entity_component(net, 'AUSF', 7021, 2)
    sba_entity_component(net, 'UDM', 7031, 3)
    sba_entity_component(net, 'AMF', 7041, 4)
    sba_entity_component(net, 'SMF', 7051, 5, switch_cnt=2)
    sba_entity_component(net, 'PCF', 7061, 6)
    sba_entity_component(net, 'AF', 7071, 7)

    # Data Plane
    data_plane(net, 8001)

    # Link UAM switch to NFV Services' controllers
    net.addLink(switches['uam'][0], switches['n_URLLC'][0])
    net.addLink(switches['uam'][0], switches['n_eMBB'][0])
    net.addLink(switches['uam'][0], switches['n_mMTC'][0])

    # Link NFV Services to AMF
    net.addLink(switches['n_URLLC'][0], switches['s_AMF'][0])
    net.addLink(switches['n_eMBB'][0], switches['s_AMF'][0])
    net.addLink(switches['n_mMTC'][0], switches['s_AMF'][0])

    # Link SBA Entities as a chain
    net.addLink(switches['s_AMF'][0], switches['s_UDM'][0])
    net.addLink(switches['s_UDM'][0], switches['s_AUSF'][0])
    net.addLink(switches['s_AUSF'][0], switches['s_NRF'][0])
    net.addLink(switches['s_AMF'][0], switches['s_SMF'][0])
    net.addLink(switches['s_SMF'][0], switches['s_PCF'][0])
    net.addLink(switches['s_PCF'][0], switches['s_AF'][0])

    # Link Control Plane and Data Plane
    net.addLink(switches['s_SMF'][1], switches['d_UPF'][0])
    net.addLink(switches['uam'][0], switches['d_UPF'][0])

    # Add UE
    add_ue(net, 'URLLC', '10.0.1.101')
    add_ue(net, 'eMBB', '10.0.1.102')
    add_ue(net, 'mMTC', '10.0.1.103')

    return net


def add_ue(net, name, ip='10.0.0.101'):
    "add UE"

    # add UE host
    hosts['ue_' + name] = [
        net.addHost('ue_' + name + '_h', ip=ip)
    ]

    # link UE host to UAM
    net.addLink(switches['uam'][0], hosts['ue_' + name][0])


def ue_access_component(net, controller_port=6661):
    "add UE Access Component topo"

    info('*** Starting UE Access Controller at {}\n'.format(controller_port))
    add_subsystem(net, 'uam', controller_port, '10.0.1.1', 1)


def nfv_service_component(net, scenario=None, controller_port=6671, no=1):
    "add NFV Service Component topo"
    if not scenario:
        info('*** NFV Scenario Missing ***\n')
        return

    info('*** Starting NFV Service-{} Controller at {}\n'.format(scenario, controller_port))
    add_subsystem(net, 'n_' + scenario, controller_port,
                  '10.0.2.' + str(no), 1)


def sba_entity_component(net, name=None, controller_port=7011, no=1, switch_cnt=1):
    "add SBA Entity Component topo"
    if not name:
        info('*** SBA Entity Name Missing ***\n')
        return

    info('*** Starting SBA Entity-{} Controller at {}\n'.format(name, controller_port))
    add_subsystem(net, 's_' + name, controller_port,
                  '10.0.3.' + str(no), switch_cnt)


def data_plane(net, controller_port=8001):
    "add data plane topo for experiment"

    info('*** Starting data plane\n')
    info('*** Starting UPF Controller at {}\n'.format(controller_port))
    add_subsystem(net, 'd_UPF', controller_port, '10.0.4.1', 1)
    hosts['d_UPF'].append(net.addHost('d_DN', ip='10.0.5.1'))
    net.addLink(switches['d_UPF'][0], hosts['d_UPF'][1])


def add_subsystem(net, name=None, controller_port=6661, host_ip='10.0.0.1', switch_cnt=1):
    "Add a SDN-based subsystem"
    global dpid_cnt

    if not name:
        info('*** Subsystem Name Missing ***\n')
        return

    controllers[name] = net.addController(
        name + '_c0',
        controller=RemoteController,
        port=controller_port
    )
    # switches[name] = [
    #     net.addSwitch(name + '_s{}'.format(i), dpid=str(dpid_cnt))
    #     for i in range(switch_cnt)
    # ]
    switches[name] = []
    for i in range(switch_cnt):
        switches[name].append(net.addSwitch(name + '_s{}'.format(i), dpid=hex(dpid_cnt)[2:]))
        dpid_cnt += 1
    hosts[name] = [
        net.addHost(name + '_h0', ip=host_ip)
    ]

    # Add link between switch and host
    net.addLink(switches[name][0], hosts[name][0])

    # Add link between all switches:
    if switch_cnt > 1:
        for i in range(switch_cnt - 1):
            for j in range(i + 1, switch_cnt):
                net.addLink(switches[name][i], switches[name][j])


if __name__ == "__main__":
    setLogLevel('info')

    net = DistrubutedSBANet()

    info('*** Starting Distributed SDN-based 5G Core Network\n')
    net.build()

    # Start controllers
    for k, c in controllers.items():
        c.start()

    # Start switches with their controller
    for k, comp in switches.items():
        for switch in comp:
            switch.start([controllers[k]])
            # switch.start([])

    # mininet.ns3.start()

    # info('*** Dumping all Controller, Switch and Hosts\n')
    # print controllers
    # print switches
    # print hosts

    # info('*** Testing Hosts')
    # net.pingAll()

    info('*** Running CLI\n')
    # info(pprint.pformat(controllers, indent=4) + '\n')
    # info(pprint.pformat(switches, indent=4) + '\n')
    # info(pprint.pformat(hosts, indent=4) + '\n')
    CLI(net)

    info('*** Stopping network')
    # mininet.ns3.clear()
    net.stop()
