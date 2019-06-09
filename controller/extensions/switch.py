from pox.core import core
import pox.openflow.libopenflow_01 as of

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
        if self.dpid == 5:
            msg = of.ofp_flow_mod()
            msg.match = of.ofp_match.from_packet(packet, event.port)
            msg.idle_timeout = 10
            msg.hard_timeout = 30
            msg.actions.append(of.ofp_action_output(port=3))
            msg.data = event.ofp
            self.connection.send(msg)

        if self.dpid == 2:
            msg = of.ofp_flow_mod()
            msg.match = of.ofp_match.from_packet(packet, event.port)
            msg.idle_timeout = 10
            msg.hard_timeout = 30
            msg.actions.append(of.ofp_action_output(port=self.main_controller.ports[2][5]))
            msg.data = event.ofp
            self.connection.send(msg)

        if self.dpid == 1:
            msg = of.ofp_flow_mod()
            msg.match = of.ofp_match.from_packet(packet, event.port)
            msg.idle_timeout = 10
            msg.hard_timeout = 30
            msg.actions.append(of.ofp_action_output(port=self.main_controller.ports[1][2]))
            msg.data = event.ofp
            self.connection.send(msg)

        # log.info("Packet arrived to switch %s from %s to %s", self.dpid, packet.src, packet.dst)
