import pytest

from chainup.host import Host


def test_connect():
    host = Host('10.1.1.30', 'root', 'kk', 22, 'test')
    host.try_connect()
    host.close()
