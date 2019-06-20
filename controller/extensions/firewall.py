from pox.core import core
import pox.lib.packet as pkt
from pox.lib.recoco import Timer
import pox.openflow.libopenflow_01 as of

log = core.getLogger()


class FireWall:
    MAX_UDP_PACKETS = 10
    PROTOCOLS_TO_BLOCK = [pkt.ipv4.UDP_PROTOCOL, pkt.ipv4.ICMP_PROTOCOL]  # TODO: sacar ICMP, es solo para probar con ping
    CHECK_TIME = 20

    def __init__(self):
        self.should_drop = False
        self.packets_by_destiny = {}
        self.blocked = []
        core.openflow.addListenerByName(
            "FlowStatsReceived",
            self._handle_flowstats_received
        )
        self.reports_by_sw = {}

    def _handle_flowstats_received(self, event):
        """
        Esta funcion se llama cada CHECK_TIME segundos. Si en ese lapso, la cantidad de paquetes supera
        MAX_UDP_PACKETS se aplica blackhole, sino, si estaba bloqueada se desbloquea
        """
        log.info("Checking for DoS attack")
        self.packets_by_destiny = {}
        for flow in event.stats:
            dst = flow.match.nw_dst
            dpid = event.connection.dpid
            reports = self.reports_by_sw.get(dpid, set())

            if flow.match.nw_proto in self.PROTOCOLS_TO_BLOCK:
                packets_count = self.packets_by_destiny.get(dst, 0) + flow.packet_count
                self.packets_by_destiny[dst] = packets_count
                log.info("Packet count to {}: {}".format(dst, self.packets_by_destiny[dst]))
                self.apply_blackholing()
                reports.add(dst)
            else:
                if dst in reports:
                    reports.remove(dst)

            self.reports_by_sw[dpid] = reports

        self.clear_blocked()

    def apply_blackholing(self):
        for dst, pkt_count in self.packets_by_destiny.items():
            if pkt_count >= self.MAX_UDP_PACKETS:
                self.block_dst(dst)
            else:
                self.unblock_dst(dst)

    def clear_blocked(self):
        """
        Hasta que los sw que reportaron paquetes UDP a un host, no reporten mas, no se desbloquea el destino
        """
        for dst in self.blocked:
            if not [reports for reports in self.reports_by_sw.values() if dst in reports]:
                self.unblock_dst(dst)

    def unblock_dst(self, dst):
        if dst in self.blocked:
            log.info("Unblocking traffic to {}".format(dst))
            self.blocked.remove(dst)

            msg = of.ofp_flow_mod()
            msg.match.dl_type = pkt.ethernet.IP_TYPE
            msg.command = of.OFPFC_DELETE
            msg.match.nw_dst = dst

            for connection in core.openflow.connections:
                connection.send(msg)

    def block_dst(self, dst):
        if dst not in self.blocked:
            log.info("Blocking traffic to {}".format(dst))
            self.blocked.append(dst)
            msg = of.ofp_flow_mod()
            msg.priority = of.OFP_DEFAULT_PRIORITY + 1
            msg.match.dl_type = pkt.ethernet.IP_TYPE
            msg.match.nw_dst = dst

            for connection in core.openflow.connections:
                connection.send(msg)

    def request_switch_statistics(self):
        for connection in core.openflow.connections:
            body = of.ofp_flow_stats_request()
            connection.send(of.ofp_stats_request(body=body))

    def start(self, **kwargs):
        Timer(self.CHECK_TIME, self.request_switch_statistics, recurring=True)
