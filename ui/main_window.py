from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout
from ui.top_ribbon import TopRibbon
from ui.timeline import Timeline
from ui.track_area import TrackArea
from audio_engine import AudioEngine

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("My DAW")
        self.showMaximized()

        self.engine = AudioEngine()

        central = QWidget()
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(5)

        self.top_ribbon = TopRibbon()
        self.timeline = Timeline()
        self.track_area = TrackArea()

        main_layout.addWidget(self.top_ribbon)
        main_layout.addWidget(self.timeline)
        main_layout.addWidget(self.track_area)

        self.setCentralWidget(central)

        # Connect buttons to engine methods
        self.top_ribbon.play_btn.clicked.connect(self.engine.play)
        self.top_ribbon.pause_btn.clicked.connect(self.engine.pause)
        self.top_ribbon.stop_btn.clicked.connect(self.engine.stop)


