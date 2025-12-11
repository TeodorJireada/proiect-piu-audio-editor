import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from ui.main_window import MainWindow
from ui.theme_manager import ThemeManager

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("DAW proiect PIU")
    app.setWindowIcon(QIcon('assets/logo.png'))
    
    ThemeManager.apply_theme(app)
    
    window = MainWindow()
    window.showMaximized()
    sys.exit(app.exec())