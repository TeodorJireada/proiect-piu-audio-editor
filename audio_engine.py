from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtCore import QUrl, QObject, pyqtSignal
from pathlib import Path

class AudioEngine(QObject):
    positionChanged = pyqtSignal(int)
    durationChanged = pyqtSignal(int)
    playbackStateChanged = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        project_root = Path(__file__).resolve().parent.parent
        audio_file = project_root / "assets" / "perennialquest.opus"

        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.player.setSource(QUrl.fromLocalFile(str(audio_file)))

        self.player.positionChanged.connect(self.positionChanged)
        self.player.durationChanged.connect(self.durationChanged)
        self.player.playbackStateChanged.connect(self.playbackStateChanged)
    
    def play(self):
        self.player.play()

    def pause(self):
        self.player.pause()

    def stop(self):
        self.player.stop()

    def set_position(self, ms):
        self.player.setPosition(ms)

    def position(self):
        return self.player.position()

    def duration(self):
        return self.player.duration()