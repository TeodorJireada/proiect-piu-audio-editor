from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtCore import QUrl, Qt
from pathlib import Path
import pyqtgraph as pg
import numpy as np
import soundfile as sf
from ui.slider_widget import ClickableSlider

class AudioPlayer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simple Audio Player with Waveform")
        self.resize(600, 400)

        # Layout
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Buttons
        self.play_pause_button = QPushButton("Play")
        self.stop_button = QPushButton("Stop")

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.play_pause_button)
        buttons_layout.addWidget(self.stop_button)
        layout.addLayout(buttons_layout)

        # Waveform view
        self.waveform_plot = pg.PlotWidget()
        self.waveform_plot.setMenuEnabled(False)
        self.waveform_plot.showGrid(x=True, y=True, alpha=0.3)
        self.waveform_plot.setLabel('bottom', 'Time', units='s')
        self.waveform_plot.setLabel('left', 'Amplitude')
        layout.addWidget(self.waveform_plot, stretch=1)

        # Timeline slider (global)
        self.timeline_slider = ClickableSlider(Qt.Orientation.Horizontal)
        layout.addWidget(self.timeline_slider)

        # Time label
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.time_label)

        # Audio setup
        project_root = Path(__file__).resolve().parent.parent
        audio_file = project_root / "assets" / "perennialquest.opus"

        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.player.setSource(QUrl.fromLocalFile(str(audio_file)))

        # Load waveform
        self.load_waveform(str(audio_file))

        # Connect buttons
        self.play_pause_button.clicked.connect(self.toggle_play_pause)
        self.stop_button.clicked.connect(self.stop_audio)

        # Connect progress updates
        self.player.durationChanged.connect(self.update_duration)
        self.player.positionChanged.connect(self.update_position)
        self.timeline_slider.sliderMoved.connect(self.set_project_position)

        self.update_timeline_range()

        # Internal variables
        self.duration = 0

    def set_project_position(self, position_ms):
        self.player.setPosition(position_ms)

    def load_waveform(self, path):
        try:
            data, samplerate = sf.read(path)
            if data.ndim > 1:
                data = np.mean(data, axis = 1) # stereo -> mono
            times = np.linspace(0, len(data) / samplerate, num=len(data))

            max_points = 5000
            if len(data) > max_points:
                factor = len(data) // max_points
                data = data[::factor]
                times = np.linspace(0, len(data) / samplerate, num=len(data))
            
            self.waveform_plot.clear()
            self.waveform_plot.plot(times, data, pen='c')

        except Exception as e:
            print("Error loading waveform: ", e)

    def toggle_play_pause(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            self.play_pause_button.setText("Play")
        else:
            self.player.play()
            self.play_pause_button.setText("Pause")

    def stop_audio(self):
        self.player.stop()
        self.play_pause_button.setText("Play")
        self.timeline_slider.setValue(0)
        self.update_time_label(0, self.duration)

    def update_timeline_range(self):
        if hasattr(self, 'player'):
            duration = self.player.duration()
            self.timeline_slider.setRange(0, duration)

    def update_duration(self, duration):
        self.duration = duration
        self.timeline_slider.setRange(0, duration)
        self.update_time_label(0, duration)

    def update_position(self, position):
        if not self.timeline_slider.isSliderDown():
            self.timeline_slider.setValue(position)
        self.update_time_label(position, self.timeline_slider.maximum())

    def set_position(self, position):
        self.player.setPosition(position)

    def update_time_label(self, position, duration):
        def format_time(ms):
            seconds = ms // 1000
            minutes = seconds // 60
            seconds = seconds % 60
            return f"{minutes:02d}:{seconds:02d}"

        current_time = format_time(position)
        total_time = format_time(duration)
        self.time_label.setText(f"{current_time} / {total_time}")
