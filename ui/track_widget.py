from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
import pyqtgraph as pg
import numpy as np

class TrackWidget(QWidget):
    def __init__(self, track_name: str, waveform_data: np.ndarray, samplerate: int):
        super().__init__()
        self.track_name = track_name
        self.waveform_data = waveform_data
        self.samplerate = samplerate

        self.setFrameShape(QFrame.Shape.Box)
        self.setFixedHeight(80)

        layout = QVBoxLayout()
        self.setLayout(layout)

        # Track label
        self.label = QLabel(track_name)
        layout.addWidget(self.label)

        # Waveform plot
        self.waveform_plot = pg.PlotWidget()
        self.waveform_plot.setMenuEnabled(False)
        self.waveform_plot.showGrid(x=True, y=True, alpha=0.2)
        self.waveform_plot.setLabel('bottom', 'Time', units='s')
        self.waveform_plot.setLabel('left', 'Amplitude')
        layout.addWidget(self.waveform_plot)

        self.plot_waveform()

    def plot_waveform(self, max_points=5000):
        data = self.waveform_data
        if data.ndim > 1:
            data = np.mean(data, axis=1)
        
        times = np.linspace(0, len(data)/self.samplerate, num=len(data))

        if len(data) > max_points:
            factor = len(data) // max_points
            data = data[::factor]
            times = np.linspace(0, len(data)/self.samplerate, num=len(data))

        self.waveform_plot.clear()
        self.waveform_plot.plot(times, data, pen='c')