from PySide6.QtCore import Qt, QRect, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QBrush
from PySide6.QtWidgets import QFrame

class TrackLane(QFrame):
    clip_moved = Signal(int, float) # clip_index, new_start_time

    def __init__(self):
        super().__init__()
        self.setObjectName("TrackLane")
        self.setFixedHeight(80)
        self.setMinimumWidth(3000)
        self.clips = [] 
        self.playhead_x = 0
        self.pixels_per_second = 100
        self.duration = 60
        self.is_placeholder = False
        
        # Dragging State
        self.dragging_clip_index = -1
        self.drag_start_x = 0
        self.clip_initial_start_time = 0.0

    def set_zoom(self, px_per_sec):
        self.pixels_per_second = px_per_sec
        self.update_width()
        self.update()

    def set_duration(self, duration):
        self.duration = duration
        self.update_width()
        self.update()

    def update_width(self):
        width = int(self.duration * self.pixels_per_second)
        self.setMinimumWidth(width)

    def add_clip(self, name, start_time, duration, color, waveform=None):
        self.clips.append({
            "name": name,
            "start_time": start_time,
            "duration": duration,
            "color": color,
            "waveform": waveform
        })
        self.update()

    def set_playhead(self, x):
        self.playhead_x = x
        self.update()

    def mousePressEvent(self, event):
        if self.is_placeholder: return
        
        if event.button() == Qt.LeftButton:
            click_x = event.position().x()
            
            # Check if clicked on a clip
            for i, clip in enumerate(self.clips):
                start_x = int(clip['start_time'] * self.pixels_per_second)
                width = int(clip['duration'] * self.pixels_per_second)
                end_x = start_x + width
                
                if start_x <= click_x <= end_x:
                    self.dragging_clip_index = i
                    self.drag_start_x = click_x
                    self.clip_initial_start_time = clip['start_time']
                    break

    def mouseMoveEvent(self, event):
        if self.dragging_clip_index != -1:
            current_x = event.position().x()
            delta_x = current_x - self.drag_start_x
            
            delta_time = delta_x / self.pixels_per_second
            new_start_time = self.clip_initial_start_time + delta_time
            
            if new_start_time < 0: new_start_time = 0
            
            self.clips[self.dragging_clip_index]['start_time'] = new_start_time
            self.update()

    def mouseReleaseEvent(self, event):
        if self.dragging_clip_index != -1:
            if event.button() == Qt.LeftButton:
                final_start_time = self.clips[self.dragging_clip_index]['start_time']
                
                # Emit signal
                # Note: We are assuming 1 clip per lane for now as per current architecture, 
                # but passing index 0 is safer if we stick to that assumption, 
                # or we can pass the clip index if we support multiple.
                # The AudioEngine track index corresponds to the Lane index, not the clip index within the lane.
                # However, the signal needs to tell the MainWindow which Lane emitted it.
                # Since the signal is on the Lane instance, MainWindow knows which lane it is.
                # So we just pass the new time.
                
                self.clip_moved.emit(self.dragging_clip_index, final_start_time)
                
                self.dragging_clip_index = -1

    def paintEvent(self, event):
        painter = QPainter(self)
        
        # Draw Clips
        mid_y = self.height() / 2 
        
        for clip in self.clips:
            start_x = int(clip['start_time'] * self.pixels_per_second)
            width = int(clip['duration'] * self.pixels_per_second)
            
            # Draw Clip Background
            clip_rect = QRect(start_x, 5, width, 70)
            painter.setBrush(QBrush(QColor(30, 30, 40))) 
            painter.setPen(QColor(clip['color']))        
            painter.drawRoundedRect(clip_rect, 3, 3)

            # DRAW WAVEFORM
            if clip['waveform'] is not None:
                wave_color = QColor(clip['color'])
                wave_color.setAlpha(200)
                painter.setPen(wave_color)
                
                waveform = clip['waveform']
                
                # Waveform is currently sampled at 100 samples/sec (hardcoded in track_loader)
                # We need to scale it to current pixels_per_second
                
                # Original samples per second (from track_loader)
                original_sps = 100 
                
                # We want to draw 'width' pixels
                # We have 'len(waveform)' samples covering 'duration' seconds
                
                # Simple approach: Iterate pixels and map to waveform index
                for x in range(width):
                    # Time at this pixel relative to clip start
                    t = x / self.pixels_per_second
                    
                    # Index in waveform array
                    idx = int(t * original_sps)
                    
                    if idx < len(waveform):
                        val = float(waveform[idx])
                        bar_height = val * 35 
                        
                        x_draw = start_x + x
                        y1 = int(mid_y - bar_height)
                        y2 = int(mid_y + bar_height)
                        
                        painter.drawLine(x_draw, y1, x_draw, y2)

            # Draw Clip Name Overlay
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(clip_rect.adjusted(5, 5, 0, 0), Qt.AlignLeft | Qt.AlignTop, clip['name'])

        # Draw Playhead
        painter.setPen(QPen(QColor(255, 50, 50, 180), 1))
        playhead_int = int(self.playhead_x)
        painter.drawLine(playhead_int, 0, playhead_int, self.height())