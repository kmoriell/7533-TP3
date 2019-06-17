from datetime import datetime


class TCAM:
    def __init__(self):
        self.table = {}

    def __str__(self):
        return str(self.table)

    def get(self, _tuple):
        try:
            path, timestamp = self.table[_tuple]
            if (datetime.now() - timestamp).total_seconds() > 5:
                del self.table[_tuple]
                return None
            return path
        except KeyError:
            return None

    def set(self, _tuple, path):
        self.table[_tuple] = (path, datetime.now())
