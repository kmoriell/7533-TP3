import networkx as nx
import pox.forwarding.l2_learning
import pox.openflow.discovery
import pox.openflow.spanning_tree
from pox.core import core
from pox.host_tracker.host_tracker import host_tracker
from pox.lib.util import dpid_to_str

from extensions.switch import SwitchController

log = core.getLogger()


class Controller:
    MAX_UDP_PACKETS = 10  # pkts/seg
    TIMER = 10  # segs
    paquetes_por_destino = dict()

    def __init__(self):
        self.connections = set()
        self.switches = []
        self.topology = nx.Graph()
        self.ports = {}
        self.host_tracker = host_tracker()

        # Esperando que los modulos openflow y openflow_discovery esten listos
        core.call_when_ready(self.startup, ('openflow', 'openflow_discovery'))

    def startup(self):
        """
        Esta funcion se encarga de inicializar el controller
        Agrega el controller como event handler para los eventos de
        openflow y openflow_discovery
        """
        core.openflow.addListeners(self)
        core.openflow_discovery.addListeners(self)
        # log.info('Controller initialized')

    def _handle_ConnectionUp(self, event):
        """
        Esta funcion es llamada cada vez que un nuevo switch establece conexion
        Se encarga de crear un nuevo switch controller para manejar los eventos de cada switch
        """
        # log.info("Switch %s has come up.", dpid_to_str(event.dpid))
        if (event.connection not in self.connections):
            self.connections.add(event.connection)
            sw = SwitchController(event.dpid, event.connection, self)
            self.switches.append(sw)

    def _handle_PacketIn(self, event):
        """
        Esta funcion es llamada cada que vez que se recibe un paquete.
        Aca es donde se va a implementar el firewall unicamente para paquetes UDP con un mismo
        destino que excedan un limite predefinido por unidad de tiempo.
        """
        log.info("Nuevo paquete recibido")
        # frame = event.parsed
        #
        # if frame.type == frame.IP_TYPE:
        #     packet = frame.payload
        #     if packet.protocol == packet.ICMP_PROTOCOL or packet.protocol == packet.UDP_PROTOCOL:
        #         if not packet.dstip in self.paquetes_por_destino.keys():
        #             self.paquetes_por_destino[packet.dstip] = 0
        #         self.paquetes_por_destino[packet.dstip] += 1
        #
        #         if self.paquetes_por_destino[packet.dstip] >= self.MAX_UDP_PACKETS:
        #             # log.info("Paquete bloqueado desde " + str(packet.dstip))
        #             event.halt = True
        #         Timer(self.TIMER, self.reiniciar_bloqueos)

        self.host_tracker._handle_openflow_PacketIn(event)

        for eth_addr, mac_entry in self.host_tracker.entryByMAC.iteritems():
            # { dest_dpid: { source_dpid: dest_port } }
            if not self.ports.get(mac_entry.dpid):
                self.ports[mac_entry.dpid] = {}
            self.ports[mac_entry.dpid][eth_addr.to_str()] = mac_entry.port

            self.topology.add_edge(eth_addr.to_str(), mac_entry.dpid)

    def reiniciar_bloqueos(self):
        self.paquetes_por_destino.clear()

    def handle_link_up(self, link):
        self.topology.add_edge(link.dpid1, link.dpid2)

        # { source_dpid: { dest_dpid: source_port } }

        if not self.ports.get(link.dpid1):
            self.ports[link.dpid1] = {}
        self.ports[link.dpid1][link.dpid2] = link.port1

        # { dest_dpid: { source_dpid: dest_port } }

        if not self.ports.get(link.dpid2):
            self.ports[link.dpid2] = {}
        self.ports[link.dpid2][link.dpid1] = link.port2

        log.info("Link has been discovered from %s,%s to %s,%s", dpid_to_str(link.dpid1), link.port1,
                 dpid_to_str(link.dpid2), link.port2)

    def handle_link_down(self, link):
        try:
            self.topology.remove_edge(link.dpid1, link.dpid2)

            del self.ports[link.dpid1][link.dpid2]
            del self.ports[link.dpid2][link.dpid1]

            log.info("Link has been removed from %s,%s to %s,%s", dpid_to_str(link.dpid1), link.port1,
                     dpid_to_str(link.dpid2), link.port2)
        except nx.NetworkXError:
            pass  # ya se borro (borra 2 veces, es bidireccional, y nosotros queremos borrar una vez)

    def _handle_LinkEvent(self, event):
        """
        Esta funcion es llamada cada vez que openflow_discovery descubre un nuevo enlace
        """
        link = event.link

        if event.added:
            self.handle_link_up(link)
        elif event.removed:
            self.handle_link_down(link)

def launch():
    # Inicializando el modulo openflow_discovery
    pox.openflow.discovery.launch()

    # Registrando el Controller en pox.core para que sea ejecutado
    core.registerNew(Controller)
