from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QColor, QPainter, QPen, QBrush
from PySide6.QtWidgets import QFrame

class TrackLane(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("TrackLane")
        self.setFixedHeight(80)
        self.setMinimumWidth(3000)
        self.clips = [] 
        self.playhead_x = 0

    def add_clip(self, name, start_x, width, color, waveform=None):
        self.clips.append({
            "name": name,
            "start": start_x,
            "width": width,
            "color": color,
            "waveform": waveform
        })
        self.update()

    def set_playhead(self, x):
        self.playhead_x = x
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        
        # Draw Background Grid
        painter.setPen(QColor(40, 40, 40))
        for i in range(0, self.width(), 100): 
            painter.drawLine(i, 0, i, self.height())

        # Draw Clips
        mid_y = self.height() / 2 
        
        for clip in self.clips:
            start = clip['start']
            width = clip['width']
            
            # Draw Clip Background
            clip_rect = QRect(start, 5, width, 70)
            painter.setBrush(QBrush(QColor(30, 30, 40))) 
            painter.setPen(QColor(clip['color']))        
            painter.drawRoundedRect(clip_rect, 3, 3)

            # DRAW WAVEFORM
            if clip['waveform'] is not None:
                wave_color = QColor(clip['color'])
                wave_color.setAlpha(200)
                painter.setPen(wave_color)
                
                waveform = clip['waveform']
                
                for x, val in enumerate(waveform):
                    if x >= width: break 
                    
                    # Fix numpy types
                    val = float(val)
                    
                    bar_height = val * 35 
                    
                    # Strict Int Casting
                    x1 = int(start + x)
                    y1 = int(mid_y - bar_height)
                    x2 = int(start + x)
                    y2 = int(mid_y + bar_height)
                    
                    painter.drawLine(x1, y1, x2, y2)

            # Draw Clip Name Overlay
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(clip_rect.adjusted(5, 5, 0, 0), Qt.AlignLeft | Qt.AlignTop, clip['name'])

        # Draw Playhead
        painter.setPen(QPen(QColor(255, 50, 50, 180), 1))
        playhead_int = int(self.playhead_x)
        painter.drawLine(playhead_int, 0, playhead_int, self.height())