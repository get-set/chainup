import time


class Utils(object):
    @staticmethod
    def time_stamp():
        return time.strftime("[%H:%M:%S] ", time.localtime())
