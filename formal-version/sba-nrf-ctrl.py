from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet, ether_types, arp

# REST Api Packages
import json
import logging
from ryu.app.wsgi import WSGIApplication, ControllerBase, route
from webob import Response

sba_instance_name = 'SBA_NRF'


class SBAnrfCtrl(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {'wsgi': WSGIApplication}

    def __init__(self, *args, **kwargs):
        super(SBAnrfCtrl, self).__init__(*args, **kwargs)
        self.mac_to_port = {}  # mac address to inbound port table
        self.arp_broadcast = {}  # arp broadcast inbound port table
        wsgi = kwargs['wsgi']
        wsgi.register(EastWestAPI, {sba_instance_name: self})

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # install table-miss flow entry
        #
        # We specify NO BUFFER to max_len of the output action due to
        # OVS bug. At this moment, if we specify a lesser number, e.g.,
        # 128, OVS will send Packet-In with invalid buffer_id and
        # truncated packet data. In that case, we cannot output packets
        # correctly.  The bug has been fixed in OVS v2.1.0.
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        # If you hit this you might want to increase
        # the "miss_send_length" of your switch
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes",
                              ev.msg.msg_len, ev.msg.total_len)
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        dst = eth.dst
        src = eth.src
        dpid = datapath.id

        # ignore lldp and ipv6 packet
        if eth.ethertype == ether_types.ETH_TYPE_LLDP or eth.ethertype == ether_types.ETH_TYPE_IPV6:
            return

        self.logger.info("Packet In: %s %s -> %s | port:%s",
                         dpid, src, dst, in_port)

        if eth.ethertype == ether_types.ETH_TYPE_ARP and dst == "ff:ff:ff:ff:ff:ff":
            arp_dst_ip = pkt.get_protocol(arp.arp).dst_ip
            if (dpid, src, arp_dst_ip) in self.arp_broadcast:
                if self.arp_broadcast[(dpid, src, arp_dst_ip)] != in_port:
                    out = datapath.ofproto_parser.OFPPacketOut(
                        datapath=datapath,
                        buffer_id=datapath.ofproto.OFP_NO_BUFFER,
                        in_port=in_port,
                        actions=[], data=None)
                    datapath.send_msg(out)
                    self.logger.info('ARP Loop Maker Dropped!')

                    return
            else:  # learn arp broadcast table
                self.arp_broadcast[(dpid, src, arp_dst_ip)] = in_port

        self.mac_to_port.setdefault(dpid, {})
        # learn a mac address to avoid FLOOD next time.
        self.mac_to_port[dpid][src] = in_port

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        # install a flow to avoid packet_in next time
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
            # verify if we have a valid buffer_id, if yes avoid to send both
            # flow_mod & packet_out
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.add_flow(datapath, 1, match, actions, msg.buffer_id)
                return
            else:
                self.add_flow(datapath, 1, match, actions)
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)


class EastWestAPI(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(EastWestAPI, self).__init__(req, link, data, **config)
        self.NRF_app = data[sba_instance_name]
        self.logger = logging.getLogger(self.__class__.__name__)
        self.authentication = {
            'TEST': '033bd94b1168d7e4f0d644c3c95e35bf',
            'URLLC': 'dfdc323ef40c8f38f5f022a5554f2dee',
            'EMBB': 'e9406f9b456569f230a23d21464189f2',
            'MMTC': '1d99331a7879c3c5b90998f8c3c6a9d6'
        }
        self.unauthenticated = Response(
            status=401,
            content_type='application/json',
            body=json.dumps(
                {'error': 'unauthenticated'},
                indent=4
            ) + '\n'
        )

    @route('mac-port-table', '/mac-port-table', methods=['GET'])
    def _mac_port_table(self, req, **kwargs):
        NRF_app = self.NRF_app
        body = json.dumps(NRF_app.mac_to_port, indent=4) + '\n'

        if 'Authentication' in req.headers:
            if req.headers['Authentication'] in self.authentication.values():
                return Response(content_type='application/json', body=body)
            else:
                return self.unauthenticated
        else:
            return self.unauthenticated

    @route('arp-table', '/arp-table', methods=['GET'])
    def _arp_table(self, req, **kwargs):
        arp_broadcast = self.NRF_app.arp_broadcast
        arp_str_table = {}
        for key in arp_broadcast.keys():
            arp_str_table[str(key)] = arp_broadcast[key]
        body = json.dumps(arp_str_table, indent=4) + '\n'

        if 'Authentication' in req.headers:
            if req.headers['Authentication'] in self.authentication.values():
                return Response(content_type='application/json', body=body)
            else:
                return self.unauthenticated
        else:
            return self.unauthenticated
