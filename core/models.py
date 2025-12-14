class AudioClip:
    def __init__(self, data, start_time, start_offset, duration, name, waveform=None):
        self.data = data 
        self.start_time = start_time 
        self.start_offset = start_offset 
        self.duration = duration 
        self.name = name
        self.waveform = waveform

class AudioTrackData:
    def __init__(self, name, file_path, data, sample_rate):
        self.name = name
        self.file_path = file_path
        self.source_data = data
        self.sample_rate = sample_rate
        self.waveform = None
        self.is_muted = False
        self.is_soloed = False
        self.volume = 1.0
        self.pan = 0.0
        self.color = "#4466aa" # Default color
        self.clips = [] # List of AudioClip
