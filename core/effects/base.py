
import numpy as np
from abc import ABC, abstractmethod

class AudioEffect(ABC):
    def __init__(self, name="Effect"):
        self.name = name
        self.active = True
        self.parameters = {} # name -> value (0.0 to 1.0 or custom range)

    @abstractmethod
    def process(self, buffer, sample_rate):
        """
        Process the audio buffer in-place or return modified buffer.
        buffer: numpy array (samples, channels)
        sample_rate: int
        """
        pass
    
    def set_param(self, name, value):
        if name in self.parameters:
            self.parameters[name] = value

    def get_param(self, name):
        return self.parameters.get(name, 0.0)
