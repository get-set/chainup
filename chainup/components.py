class Components(object):
    def __init__(self, hosts=None):
        self._hosts = hosts


class ChainNode(Components):
    def __init__(self, hosts=None):
        super().__init__(hosts)


class Ops(Components):
    def __init__(self, hosts=None):
        super().__init__(hosts)


class ChainExplorer(Components):
    def __init__(self, hosts=None):
        super().__init__(hosts)


class CaServer(Components):
    def __init__(self, hosts=None):
        super().__init__(hosts)
