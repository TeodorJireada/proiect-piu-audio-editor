
import numpy as np
from .base import AudioEffect

class Distortion(AudioEffect):
    def __init__(self):
        super().__init__("Distortion")
        self.parameters = {
            "drive": 0.0, # 0.0 to 1.0 (mapped to boost)
            "mix": 1.0
        }

    def process(self, buffer, sample_rate):
        if not self.active: return buffer
        if self.parameters["drive"] <= 0.001: return buffer
        
        drive_amount = 1.0 + (self.parameters["drive"] * 20.0) # 1x to 21x Gain
        
        # Simple Soft Clipping (ArcTan)
        pre = buffer * drive_amount
        
        wet = (2.0 / np.pi) * np.arctan(pre)
        
        mix = self.parameters["mix"]
        
        output = (buffer * (1.0 - mix)) + (wet * mix)
        
        return output
