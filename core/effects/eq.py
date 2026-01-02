
import numpy as np
from scipy.signal import sosfilt, iirfilter, zpk2sos
from .base import AudioEffect

class EQ3Band(AudioEffect):
    def __init__(self):
        super().__init__("EQ 3-Band")
        # Gains in dB (-12 to +12 typical)
        self.parameters = {
            "low_gain": 0.0,
            "mid_gain": 0.0,
            "high_gain": 0.0,
            "low_freq": 200.0,
            "high_freq": 4000.0
        }
        # State for filters (sos_state)
        self.state_low = None
        self.state_mid = None
        self.state_high = None

    def _make_peaking_filter(self, center_freq, gain_db, q, fs):
        pass

    def _design_biquad(self, type, freq, fs, gain_db, q=0.707):
        A = 10 ** (gain_db / 40.0)
        omega = 2 * np.pi * freq / fs
        sn = np.sin(omega)
        cs = np.cos(omega)
        alpha = sn / (2 * q)
        beta = np.sqrt(A + A)
        
        b = [0,0,0]
        a = [0,0,0]

        if type == "low_shelf":
            b[0] = A * ((A + 1) - (A - 1) * cs + beta * sn)
            b[1] = 2 * A * ((A - 1) - (A + 1) * cs)
            b[2] = A * ((A + 1) - (A - 1) * cs - beta * sn)
            a[0] = (A + 1) + (A - 1) * cs + beta * sn
            a[1] = -2 * ((A - 1) + (A + 1) * cs)
            a[2] = (A + 1) + (A - 1) * cs - beta * sn
            
        elif type == "high_shelf":
            b[0] = A * ((A + 1) + (A - 1) * cs + beta * sn)
            b[1] = -2 * A * ((A - 1) + (A + 1) * cs)
            b[2] = A * ((A + 1) + (A - 1) * cs - beta * sn)
            a[0] = (A + 1) - (A - 1) * cs + beta * sn
            a[1] = 2 * ((A - 1) - (A + 1) * cs)
            a[2] = (A + 1) - (A - 1) * cs - beta * sn
            
        elif type == "peaking":
             # Peaking
            b[0] = 1 + alpha * A
            b[1] = -2 * cs
            b[2] = 1 - alpha * A
            a[0] = 1 + alpha / A
            a[1] = -2 * cs
            a[2] = 1 - alpha / A
            
        # Normalize
        b = np.array(b) / a[0]
        a = np.array(a) / a[0]
        
        return np.array([[b[0], b[1], b[2], 1.0, a[1], a[2]]])

    def process(self, buffer, sample_rate):
        if not self.active: return buffer
        
        # Check buffer shape
        is_stereo = False
        if buffer.ndim == 2 and buffer.shape[1] == 2:
            is_stereo = True
        elif buffer.ndim == 1:
            buffer = buffer.reshape(-1, 1) # Force 2D
        
        out = buffer.copy()
        
        # 1. Low Shelf
        if abs(self.parameters["low_gain"]) > 0.01:
            sos_low = self._design_biquad("low_shelf", self.parameters["low_freq"], sample_rate, self.parameters["low_gain"])
            if self.state_low is None or self.state_low.shape[1] != out.shape[1]:
                self.state_low = np.zeros((1, 2, out.shape[1])) # SOS State
            
            # Apply (axis=0 is samples)
            out, self.state_low = sosfilt(sos_low, out, axis=0, zi=self.state_low)

        # 2. Mid Peaking
        if abs(self.parameters["mid_gain"]) > 0.01:
             # Center of Low/High roughly
             center = (self.parameters["low_freq"] + self.parameters["high_freq"]) / 2
             sos_mid = self._design_biquad("peaking", center, sample_rate, self.parameters["mid_gain"], q=1.0)
             
             if self.state_mid is None or self.state_mid.shape[1] != out.shape[1]:
                self.state_mid = np.zeros((1, 2, out.shape[1]))
             
             out, self.state_mid = sosfilt(sos_mid, out, axis=0, zi=self.state_mid)

        # 3. High Shelf
        if abs(self.parameters["high_gain"]) > 0.01:
            sos_high = self._design_biquad("high_shelf", self.parameters["high_freq"], sample_rate, self.parameters["high_gain"])
            if self.state_high is None or self.state_high.shape[1] != out.shape[1]:
                self.state_high = np.zeros((1, 2, out.shape[1])) 
                
            out, self.state_high = sosfilt(sos_high, out, axis=0, zi=self.state_high)
            
        return out
