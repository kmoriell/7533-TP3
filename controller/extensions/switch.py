from pox.core import core
import pox.openflow.libopenflow_01 as of
import networkx as nx

log = core.getLogger()


class SwitchController:
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
        path = nx.dijkstra_path(
            self.main_controller.topology,
            packet.src.to_str(),
            packet.dst.to_str()
        )
        msg = of.ofp_packet_out()
        msg.actions.append(of.ofp_action_output(
            port=self.main_controller.ports[self.dpid][path[path.index(self.dpid) + 1]])
        )
        msg.data = event.ofp
        msg.buffer_id = event.ofp.buffer_id
        msg.in_port = event.port
        event.connection.send(msg)
