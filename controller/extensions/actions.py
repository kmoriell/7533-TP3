import pox.openflow.libopenflow_01 as of


class Action:
    def execute(self, **kwargs):
        raise NotImplementedError()

    def next(self):
        raise NotImplementedError()


class MainAction(Action):
    def execute(self, **kwargs):
        pass

    def next(self):
        return FireWallAction()


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
    def execute(self, **kwargs):
        pass

    def next(self):
        return UpdateTableAction()
