import pox.openflow.libopenflow_01 as of
from threading import Timer
from pox.core import core

log = core.getLogger()


class Action:
    def execute(self, **kwargs):
        raise NotImplementedError()

    def next(self):
        raise NotImplementedError()


class MainAction(Action):
    def __init__(self):
        self.next_action = FireWallAction()

    def execute(self, **kwargs):
        pass

    def next(self):
        return self.next_action


class UpdateTableAction(Action):
    def execute(self, **kwargs):
        # update switch table entry, and retry with the new-found information
        port_out = kwargs["port_out"]
        event = kwargs["event"]
        _10tupla = kwargs["_10tupla"]

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

    def next(self):
        return None


class FireWallAction(Action):
    MAX_UDP_PACKETS = 10  # pkt/sec
    TIMER = 100  # segs

    def __init__(self):
        self.should_drop = False
        self.packets_by_destiny = {}

    def execute(self, **kwargs):
        # TODO: no esta expirando el timer
        # TODO: esto nose si esta bien, ya que una vez instruido el sw sobre como forwardear un pkt,
        #  hasta que eso no expira no le vuelve a preguntar al controller, por lo que el pkt/sec no es "real"
        event = kwargs["event"]

        frame = event.parsed

        if frame.type == frame.IP_TYPE:
            packet = frame.payload
            if packet.protocol == packet.ICMP_PROTOCOL or packet.protocol == packet.UDP_PROTOCOL:
                if not packet.dstip in self.packets_by_destiny.keys():
                    self.packets_by_destiny[packet.dstip] = 0
                self.packets_by_destiny[packet.dstip] += 1
                log.info(self.packets_by_destiny[packet.dstip])

                if self.packets_by_destiny[packet.dstip] >= self.MAX_UDP_PACKETS:
                    log.info("Paquete bloqueado desde " + str(packet.dstip))
                    self.should_drop = True
                    event.halt = True
                Timer(self.TIMER, self.reset)

    def next(self):
        return DropAction() if self.should_drop else UpdateTableAction()

    def reset(self):
        self.packets_by_destiny.clear()


class DropAction(Action):
    def execute(self, **kwargs):
        packet = kwargs["event"].parsed.payload
        log.info("Dropping packet desde {src} hacia {dst}".format(src=packet.srcip, dst=packet.dstip))
        pass

    def next(self):
        return None
