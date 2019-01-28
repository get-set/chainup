


class A(object):
    def __init__(self):
        self.file = None

    def __enter__(self):
        self.file = open('a', 'r')
        print(1)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.file.close()
        print(2)


with A():
    sfsf
