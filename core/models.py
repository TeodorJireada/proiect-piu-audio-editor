class AudioTrackData:
    def __init__(self, name, file_path, data, sample_rate):
        self.name = name
        self.file_path = file_path
        self.data = data
        self.sample_rate = sample_rate
        self.waveform = None
