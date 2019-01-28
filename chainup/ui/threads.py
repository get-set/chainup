from PyQt5.QtCore import QRunnable

from chainup.ui.singles import SignalsForThreads


class HostInfoUpdater(QRunnable):
    def __init__(self, host):
        super().__init__()
        self.host = host
        self.signals = SignalsForThreads()

    def run(self):
        self.host.try_connect()
        self.signals.validate_finished.emit()
