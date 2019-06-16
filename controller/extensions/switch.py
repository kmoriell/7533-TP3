from pox.core import core
import pox.openflow.libopenflow_01 as of
import networkx as nx
import pox.lib.packet as pkt
from _10Tuple import _10Tuple

log = core.getLogger()


class SwitchController:
    TCAM = {}

    def __init__(self, dpid, connection, main_controller):
        self.dpid = dpid
        self.connection = connection
        # El SwitchController se agrega como handler de los eventos del switch
        self.connection.addListeners(self)
        self.main_controller = main_controller

    def broadcast(self):
        log.info("Broadcasting packet")
        msg = of.ofp.packet_out()
        msg.buffer_id = self.event.ofp.buffer_id
        msg.actions.append(of.ofp_action_output(port=of.OFPP_FLOOD))
        msg.data = self.event.ofp
        msg.in_port = self.event.port
        self.event.connection.send(msg)

    def build_10_tuple(self, packet):
        _10tupla = None
        if packet.type != packet.IPV6_TYPE:
            if packet.payload == packet.ARP_TYPE:
                self.broadcast()
            elif packet.payload.protocol == packet.payload.TCP_PROTOCOL:
                _10tupla = _10Tuple(None, packet.src, packet.dst, 0x800, packet.payload.srcip, packet.payload.dstip,
                                    0x6, packet.payload.payload.srcport, packet.payload.payload.dstport)
            else:
                _10tupla = _10Tuple(None, packet.src, packet.dst, 0x800, None, None, None, None, None)
        elif packet.type == packet.IPV6_TYPE:
            # if packet.payload.protocol == packet.payload.TCP_PROTOCOL:
            ipv6 = packet.payload
            if ipv6.payload_type == ipv6.ICMP6_PROTOCOL:
                _10tupla = _10Tuple(None, packet.src, packet.dst, 0x86dd, packet.payload.srcip, packet.payload.dstip,
                                    58, None, None)
        return _10tupla

    def update_switch_table(self, path, event, _10tupla):
        # update switch table entry, and retry with the new-found information
        port_out = self.main_controller.ports[self.dpid][path[path.index(self.dpid) + 1]]

        msg = of.ofp_flow_mod()
        msg.data = event.ofp
        msg.buffer_id = event.ofp.buffer_id
        msg.idle_timeout = 10
        msg.hard_timeout = 30

        msg.match.dl_src = _10tupla.eth_src
        msg.match.dl_dst = _10tupla.eth_dst
        msg.match.dl_type = _10tupla.eth_type
        msg.match.nw_src = _10tupla.ip_src
        msg.match.nw_dst = _10tupla.ip_dst
        msg.match.nw_proto = _10tupla.ip_proto
        msg.match.tp_src = _10tupla.tcp_src
        msg.match.tp_dst = _10tupla.tcp_dst

        msg.actions.append(of.ofp_action_output(port=port_out))
        event.connection.send(msg)

    def _handle_PacketIn(self, event):
        """
        Esta funcion es llamada cada vez que el switch recibe un paquete
        y no encuentra en su tabla una regla para rutearlo
        """
        self.event = event
        packet = event.parsed

        log.info("Packet arrived to switch %s from %s to %s", self.dpid, packet.src, packet.dst)

        _10tupla = self.build_10_tuple(packet)

        if _10tupla not in self.TCAM.keys():
            try:
                paths = list(nx.all_shortest_paths(
                    self.main_controller.topology,
                    packet.src.to_str(),
                    packet.dst.to_str()
                ))
                paths = [path for path in paths if self.dpid in path]
                path = paths[hash(_10tupla) % len(paths)]
                self.update_switch_table(path, event, _10tupla)
                self.TCAM[_10tupla] = path
            except nx.NetworkXNoPath:
                pass
        else:
            path = self.TCAM[_10tupla]
            self.update_switch_table(path, event, _10tupla)
