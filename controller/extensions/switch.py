from pox.core import core
import pox.openflow.libopenflow_01 as of
import networkx as nx
from pox.lib.addresses import IPAddr, EthAddr
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

    def _handle_PacketIn(self, event):
        """
        Esta funcion es llamada cada vez que el switch recibe un paquete
        y no encuentra en su tabla una regla para rutearlo
        """
        packet = event.parsed

        log.info("Packet arrived to switch %s from %s to %s", self.dpid, packet.src, packet.dst)
        port_in = event.ofp.in_port

        _10tupla = None
        log.info('PKT: ' + pkt.ETHERNET.ethernet.getNameForType(packet.type))        
        if packet.type != packet.IPV6_TYPE:
        #try:
            if packet.payload == packet.ARP_TYPE:
                log.info("ARP packet")
            elif packet.payload.protocol == packet.payload.TCP_PROTOCOL:
                _10tupla = _10Tuple(port_in, packet.src, packet.dst, 0x800, packet.payload.srcip, packet.payload.dstip, 0x6, packet.payload.payload.srcport, packet.payload.payload.dstport)
            else:
                _10tupla = _10Tuple(port_in, packet.src, packet.dst, 0x800, None, None, None, None, None)
        elif packet.type == packet.IPV6_TYPE:
            #if packet.payload.protocol == packet.payload.TCP_PROTOCOL:
            ipv6 = packet.payload
            if ipv6.payload_type == ipv6.ICMP6_PROTOCOL:
                _10tupla = _10Tuple(port_in, packet.src, packet.dst, 0x86dd, packet.payload.srcip, packet.payload.dstip, 58, None, None)
            log.info(str(ipv6))

        #except:
        #    pass


        log.info("_10tupla " + str(_10tupla))

        log.info("TCAM keys = " + str(self.TCAM.keys()))

        if _10tupla not in self.TCAM.keys():        
            log.info("NO esta en TCAM")
            try:
                path = nx.dijkstra_path(
                    self.main_controller.topology,
                    packet.src.to_str(),
                    packet.dst.to_str()
                )
                log.info("path: " + str(path))
                port_out = self.main_controller.ports[self.dpid][path[path.index(self.dpid) + 1]]

                # Trafico hacia ultimo elemento de path debe ser enviado por puerto definido en port
                msg = of.ofp_flow_mod()
                msg.data = event.ofp
                msg.idle_timeout = 10
                msg.hard_timeout = 30
                msg.match.dl_src = packet.src
                msg.match.dl_dst = packet.dst            

                if packet.payload.protocol == packet.payload.TCP_PROTOCOL:
                    msg.match.dl_type = 0x800 # IPv4        
                    msg.match.nw_proto = 6 # TCP       
                    msg.match.tp_src = packet.payload.payload.srcport 
                    msg.match.tp_dst = packet.payload.payload.dstport

                    msg.match.nw_src = packet.payload.srcip 
                    msg.match.nw_dst = packet.payload.dstip
                    _10tupla = _10Tuple(port_in, packet.src, packet.dst, 0x800, packet.payload.srcip, packet.payload.dstip, 0x6, packet.payload.payload.srcport, packet.payload.payload.dstport)
                else:
                    _10tupla = _10Tuple(port_in, packet.src, packet.dst, 0x800, None, None, None, None, None)
                #elif packet.payload.protocol == packet.payload.UDP_PROTOCOL:
                self.TCAM[_10tupla] = path
                msg.actions.append(of.ofp_action_output(port = port_out))
                event.connection.send(msg)
                log.info("Installing %s.%i -> %s.%i" %(packet.src, event.ofp.in_port, packet.dst, port_out))
            except nx.NetworkXNoPath:
                pass
        else:
            log.info("Ruta ya en TCAM")
            path = self.TCAM[_10tupla]
            msg = of.ofp_packet_out()
            msg.actions.append(of.ofp_action_output(
                port=self.main_controller.ports[self.dpid][path[path.index(self.dpid) + 1]]
            ))
            msg.data = event.ofp
            event.connection.send(msg)

