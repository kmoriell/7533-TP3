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

    def build_10_tuple(self, packet):
        _10tupla = None
        if packet.type != packet.IPV6_TYPE:
            if packet.payload == packet.ARP_TYPE:
                pass
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

    def update_switch_table(self, path, event, packet):
        # update switch table entry, and retry with the new-found information
        port_out = self.main_controller.ports[self.dpid][path[path.index(self.dpid) + 1]]

        msg = of.ofp_flow_mod()
        msg.data = event.ofp

        msg.buffer_id = event.ofp.buffer_id

        msg.idle_timeout = 10
        msg.hard_timeout = 30
        msg.match.dl_src = packet.src
        msg.match.dl_dst = packet.dst

        if packet.payload.protocol == packet.payload.TCP_PROTOCOL:
            msg.match.dl_type = 0x800  # IPv4
            msg.match.nw_proto = 6  # TCP
            msg.match.tp_src = packet.payload.payload.srcport
            msg.match.tp_dst = packet.payload.payload.dstport
            msg.match.nw_src = packet.payload.srcip
            msg.match.nw_dst = packet.payload.dstip

        msg.actions.append(of.ofp_action_output(port=port_out))
        event.connection.send(msg)

    def _handle_PacketIn(self, event):
        """
        Esta funcion es llamada cada vez que el switch recibe un paquete
        y no encuentra en su tabla una regla para rutearlo
        """
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
                self.update_switch_table(path, event, packet)
                self.TCAM[_10tupla] = path
            except nx.NetworkXNoPath:
                pass
        else:
            path = self.TCAM[_10tupla]
            self.update_switch_table(path, event, packet)
