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

        if packet.src.to_str() == '00:00:00:00:00:01':
            if self.dpid == 5:
                msg = of.ofp_packet_out()
                msg.data = event.ofp
                msg.actions.append(of.ofp_action_output(port=3))
                self.connection.send(msg)
            if self.dpid == 2:
                msg = of.ofp_packet_out()
                msg.data = event.ofp
                msg.actions.append(of.ofp_action_output(port=self.main_controller.ports[2][5]))
                self.connection.send(msg)
            if self.dpid == 1:
                msg = of.ofp_packet_out()
                msg.actions.append(of.ofp_action_output(port=self.main_controller.ports[1][2]))
                msg.data = event.ofp
                msg.buffer_id = event.ofp.buffer_id
                msg.in_port = event.port
                event.connection.send(msg)

                # ^ DO THINGS LIKE THIS, WITH BUFFER ID AND IN PORT
                # msg = of.ofp_packet_out()
                # msg.data = event.ofp
                # msg.actions.append(of.ofp_action_output(port=self.main_controller.ports[1][2]))
                # self.connection.send(msg)
        else:
            if self.dpid == 5:
                msg = of.ofp_packet_out()
                msg.data = event.ofp
                msg.actions.append(of.ofp_action_output(port=self.main_controller.ports[5][2]))
                self.connection.send(msg)
            if self.dpid == 2:
                msg = of.ofp_packet_out()
                msg.data = event.ofp
                msg.actions.append(of.ofp_action_output(port=self.main_controller.ports[2][1]))
                self.connection.send(msg)
            if self.dpid == 1:
                msg = of.ofp_packet_out()
                msg.data = event.ofp
                msg.actions.append(of.ofp_action_output(port=1))
                self.connection.send(msg)

        log.info("Packet arrived to switch %s from %s to %s", self.dpid, packet.src, packet.dst)
