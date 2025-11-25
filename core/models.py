class AudioTrackData:
    def __init__(self, name, file_path, data, sample_rate):
        self.name = name
        self.file_path = file_path
        self.data = data
        self.sample_rate = sample_rate
        self.waveform = None
        self.is_muted = False
        self.is_soloed = False
        self.start_sample = 0
