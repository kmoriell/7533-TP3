from datetime import datetime
from pox.core import core

log = core.getLogger()


class TCam:
    TIMEOUT = 10  # seconds
    TCAM = {}
    timers = {}

    def add_entry(self, _10tuple, path):
        self.TCAM[_10tuple] = path
        self.timers[_10tuple] = datetime.now()

    def get(self, _10tuple):
        return self.TCAM[_10tuple]

    def contains(self, _10tuple):
        if _10tuple in self.TCAM.keys():
            return not self.entry_timeout(_10tuple)
        return False

    def entry_timeout(self, _10tuple):
        timeout = (datetime.now() - self.timers[_10tuple]).total_seconds() > self.TIMEOUT
        if timeout:
            log.info("TCAM entry timeout")
            del self.TCAM[_10tuple]
        return timeout
