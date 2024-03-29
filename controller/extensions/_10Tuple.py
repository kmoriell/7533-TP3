class _10Tuple:
    vlan_id = None
    port_in = None

    eth_src = None
    eth_dst = None

    eth_type = None
    ip_src = None
    ip_dst = None

    ip_proto = None
    tcp_src = None
    tcp_dst = None

    def __init__(self):
        pass

    def __hash__(self):
        return hash(
            (
                self.vlan_id,
                self.port_in,
                self.eth_src,
                self.eth_dst,
                self.eth_type,
                self.ip_src,
                self.ip_dst,
                self.ip_proto,
                self.tcp_dst,
                self.tcp_src
            )
        )

    def __eq__(self, other):
        if other is None:
            return False
        return (self.vlan_id == other.vlan_id and
                self.port_in == other.port_in and
                self.eth_src == other.eth_src and
                self.eth_dst == other.eth_dst and
                self.eth_type == other.eth_type and
                self.ip_src == other.ip_src and
                self.ip_dst == other.ip_dst and
                self.ip_proto == other.ip_proto and
                self.tcp_dst == other.tcp_dst and
                self.tcp_src == other.tcp_src)

    def __str__(self):
        return '{} {} {} {} {} {} {} {} {} {}'.format(
            self.vlan_id,
            self.port_in,
            self.eth_src,
            self.eth_dst,
            self.eth_type,
            self.ip_src,
            self.ip_dst,
            self.ip_proto,
            self.tcp_src,
            self.tcp_dst
        )
