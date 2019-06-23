from random import choice


class ECMPTable:
    def __init__(self):
        self.table = {}  # <dpid, <flow, port>>

    def get_port_for(self, packet, ports, dpid):
        flow = self.get_flow(packet)

        if dpid not in self.table.keys():
            # si el sw no fue registrado con ningun flow, asignarle cualquier puerto
            self.table[dpid] = {}
            self.table[dpid][flow] = choice(ports)
        elif flow not in self.table[dpid]:
            # si fue registrado, pero no con este flow, asignarle un puerto aplicando Modulo N Hash (ver RFC 2991)
            self.table[dpid][flow] = ports[hash(flow) % len(ports)]

        return self.table[dpid][flow]

    def get_flow(self, packet):
        return (
            packet.payload.srcip,
            packet.payload.dstip,
            packet.payload.protocol
        )
