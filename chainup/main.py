# -*- coding: utf-8 -*-
import sys
import cgitb

from PyQt5.QtWidgets import (QApplication, QDesktopWidget)

from chainup.window import MainWindow


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    desktop = QDesktopWidget().availableGeometry()
    width = (desktop.width() - window.width()) / 2
    height = (desktop.height() - window.height()) / 2
    window.show()
    window.move(width, height)
    sys.exit(app.exec_())


if __name__ == "__main__":
    cgitb.enable(format='text')
    main()
