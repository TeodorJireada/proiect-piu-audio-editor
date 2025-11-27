import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from ui.main_window import MainWindow


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("DAW proiect PIU")
    app.setWindowIcon(QIcon('assets/logo.png'))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())