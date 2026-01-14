
import numpy as np
from .base import AudioEffect

class SimpleDelay(AudioEffect):
    def __init__(self):
        super().__init__("Delay")
        self.parameters = {
            "time": 0.3, # Seconds
            "feedback": 0.4, # 0.0 - 0.95
            "mix": 0.3 # 0.0 - 1.0 (Wet amount)
        }
        self.buffer = None
        self.write_ptr = 0
        
    def process(self, input_buffer, sample_rate):
        if not self.active: return input_buffer
        if self.parameters["mix"] <= 0.001: return input_buffer
        
        num_samples, channels = input_buffer.shape
        delay_seconds = self.parameters["time"]
        delay_samples = int(delay_seconds * sample_rate)
        
        # Ensure buffer exists (Alloc max 2 seconds)
        max_delay_samples = int(2.0 * sample_rate)
        if self.buffer is None or self.buffer.shape[1] != channels:
            self.buffer = np.zeros((max_delay_samples, channels), dtype='float32')
            self.write_ptr = 0
            
        # Limit delay
        delay_samples = min(delay_samples, max_delay_samples - 1)
        delay_samples = max(1, delay_samples)
        
        feedback = self.parameters["feedback"]
        wet_mix = self.parameters["mix"]
        
        # Output Buffer
        output = input_buffer.copy()
        
        # Read Pointer
        read_ptr_start = self.write_ptr - delay_samples
        
        read_indices = (np.arange(num_samples) + (self.write_ptr - delay_samples)) % max_delay_samples
        write_indices = (np.arange(num_samples) + self.write_ptr) % max_delay_samples
        
        delayed_signal = self.buffer[read_indices]
        
        to_write = input_buffer + (delayed_signal * feedback)
        
        self.buffer[write_indices] = to_write
        
        self.write_ptr = (self.write_ptr + num_samples) % max_delay_samples
        
        output = (input_buffer * (1.0 - wet_mix)) + (delayed_signal * wet_mix)
        
        return output
