import numpy as np
import soundfile as sf
import scipy.signal
import os
from PySide6.QtCore import QThread, Signal
from core.models import AudioTrackData 

class TrackLoader(QThread):
    loaded = Signal(object) 
    failed = Signal(str)

    def __init__(self, file_path, target_sr):
        super().__init__()
        self.file_path = file_path
        self.target_sr = target_sr

    def run(self):
        try:
            # Load Audio
            data, fs = sf.read(self.file_path, dtype='float32', always_2d=True)
            
            # Resample if needed
            if fs != self.target_sr:
                number_of_samples = round(len(data) * float(self.target_sr) / fs)
                
                try:
                    # Attempt High-Quality Resampling
                    data = scipy.signal.resample(data, number_of_samples)
                except MemoryError:
                    # Fallback: Linear Interpolation (Low RAM usage)
                    print("[TrackLoader] Low RAM fallback for resampling")
                    indices = np.linspace(0, len(data) - 1, number_of_samples)
                    left = np.interp(indices, np.arange(len(data)), data[:, 0])
                    right = np.interp(indices, np.arange(len(data)), data[:, 1])
                    data = np.column_stack((left, right))

            # Generate Waveform for UI
            step = int(self.target_sr / 100)
            if step < 1: step = 1       # Safety check for very short sounds
            
            # Convert to Mono & Absolute value for visualization
            mono_abs = np.mean(np.abs(data), axis=1)
            
            # Decimate (take every Nth sample)
            waveform = mono_abs[::step]
            
            # Normalize waveform (0.0 to 1.0)
            if np.max(waveform) > 0:
                waveform = waveform / np.max(waveform)

            # Create the Data Object
            track_obj = AudioTrackData(
                name=os.path.basename(self.file_path),
                file_path=self.file_path,
                data=data.astype('float32'),
                sample_rate=self.target_sr
            )
            # Attach the calculated waveform to the object
            track_obj.waveform = waveform

            # Emit the object
            self.loaded.emit(track_obj)
            
        except Exception as e:
            self.failed.emit(str(e))