import networkx as nx
import pox.openflow.libopenflow_01 as of
from pox.core import core
from _10Tuple import _10Tuple
from tcam import TCam

log = core.getLogger()


class SwitchController:
    TCAM = TCam()

    def __init__(self, dpid, connection, main_controller):
        self.dpid = dpid
        self.connection = connection
        # El SwitchController se agrega como handler de los eventos del switch
        self.connection.addListeners(self)
        self.main_controller = main_controller

    def build_10_tuple(self, packet):
        _10tupla = _10Tuple()

        _10tupla.vlan_id = None
        _10tupla.port_in = None

        _10tupla.eth_src = packet.src
        _10tupla.eth_dst = packet.dst
        _10tupla.eth_type = packet.type

        if packet.type == packet.IP_TYPE or packet.type == packet.IPV6_TYPE:
            ip = packet.payload
            _10tupla.ip_src = ip.srcip
            _10tupla.ip_dst = ip.dstip
            protocol = ip.protocol if packet.type == packet.IP_TYPE else ip.payload_type
            _10tupla.ip_proto = protocol
            if protocol == ip.TCP_PROTOCOL:
                tcp = ip.payload
                _10tupla.tcp_src = tcp.srcport
                _10tupla.tcp_dst = tcp.dstport
        else:
            log.info('unknown type: {}'.format(packet.type))
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
        msg.priority = of.OFP_DEFAULT_PRIORITY

        msg.actions.append(of.ofp_action_output(port=port_out))
        event.connection.send(msg)

    def is_link_up(self, _10tupla):
        if self.TCAM.contains(_10tupla):
            path = self.TCAM.get(_10tupla)
            return path[path.index(self.dpid) + 1] in self.main_controller.ports[self.dpid]
        return False

    def _handle_PacketIn(self, event):
        """
        Esta funcion es llamada cada vez que el switch recibe un paquete
        y no encuentra en su tabla una regla para rutearlo
        """
        self.event = event
        packet = event.parsed

        log.info("Packet arrived to switch %s from %s to %s", self.dpid, packet.src, packet.dst)

        _10tupla = self.build_10_tuple(packet)

        if not self.TCAM.contains(_10tupla) or not self.is_link_up(_10Tuple):
            try:
                paths = list(nx.all_shortest_paths(
                    self.main_controller.topology,
                    packet.src.to_str(),
                    packet.dst.to_str()
                ))
                paths = [path for path in paths if self.dpid in path]
                path = self.get_path_applying_ecmp(paths, packet)
                self.update_switch_table(path, event, _10tupla)
                self.TCAM.add_entry(_10tupla, path)
            except nx.NetworkXNoPath:
                pass
        else:
            path = self.TCAM.get(_10tupla)
            self.update_switch_table(path, event, _10tupla)

    def get_path_applying_ecmp(self, paths, packet):
        possible_next_hops = set()
        for path in paths:
            possible_next_hops.add(path[path.index(self.dpid) + 1])

        log.info("Possible next hops for {}: going from {} to {}: {}".format(self.dpid, paths[0][0], paths[0][-1], possible_next_hops))

        possible_ports_by_hop = {}
        for next_hop in possible_next_hops:
            port = self.main_controller.ports[self.dpid][next_hop]
            possible_ports_by_hop[port] = next_hop

        selected_port = self.main_controller.get_port_for(packet, self.dpid, possible_ports_by_hop.keys())
        next_hop = possible_ports_by_hop[selected_port]
        log.info("Selected next hop: {}".format(next_hop))

        return [path for path in paths if next_hop in path][0]
