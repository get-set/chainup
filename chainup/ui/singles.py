from PyQt5.QtCore import QObject, pyqtSignal


class SignalsForThreads(QObject):
    validate_finished = pyqtSignal()
    
    summary_add = pyqtSignal(bool, str)
    log_append = pyqtSignal(str)
    log_overwrite_last_line = pyqtSignal(str)
    progress_value_change = pyqtSignal(int)
    finished = pyqtSignal()

