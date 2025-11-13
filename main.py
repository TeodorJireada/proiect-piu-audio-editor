import sys
from PyQt6.QtWidgets import QApplication
from ui.player_widget import AudioPlayer
from ui.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # window = AudioPlayer()

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
