from PySide6.QtWidgets import QSlider, QStyleOptionSlider, QSizePolicy
from PySide6.QtGui import QPainter, QBrush, QColor, QPen, QPalette, QPainterPath
from PySide6.QtCore import Qt, QRectF, Signal

class TimelineSlider(QSlider):
    seek_requested = Signal(float) # Emits seconds

    def __init__(self, parent=None):
        super().__init__(Qt.Horizontal, parent)
        self.setMouseTracking(True)
        self.setMinimumWidth(150) # Ribbon is wide enough
        self.setFixedHeight(34)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        self.duration = 60.0 # Default
        self.setRange(0, 10000) # High resolution
        
        self.is_user_interacting = False
        
        self.valueChanged.connect(self.on_value_changed)
        self.sliderPressed.connect(self.on_pressed)
        self.sliderReleased.connect(self.on_released)

    def set_duration(self, duration_seconds):
        self.duration = max(1.0, duration_seconds)
        self.update()

    def update_position(self, time_seconds):
        if not self.is_user_interacting:
            # Map time to 0-10000
            # Clamp time
            time_seconds = max(0.0, min(time_seconds, self.duration))
            val = int((time_seconds / self.duration) * 10000)
            self.blockSignals(True)
            self.setValue(val)
            self.blockSignals(False)
            self.update()

    def on_pressed(self):
        self.is_user_interacting = True

    def on_released(self):
        self.is_user_interacting = False

    def on_value_changed(self, value):
        if self.is_user_interacting:
            time = (value / 10000.0) * self.duration
            self.seek_requested.emit(time)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        palette = self.palette()
        
        rect = self.rect()
        
        margin = 10 
        track_height = 8 # Thicker track
        
        # Track Logic
        track_y = rect.center().y() - (track_height / 2)
        track_width = rect.width() - 2 * margin
        track_rect = QRectF(margin, track_y, track_width, track_height)
        
        # Draw Track Background
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 80)) 
        painter.drawRoundedRect(track_rect, 4, 4) # More rounded
        
        # Draw Progress
        val_range = self.maximum() - self.minimum()
        pos_ratio = (self.value() - self.minimum()) / val_range if val_range > 0 else 0
        
        progress_width = track_width * pos_ratio
        progress_rect = QRectF(track_rect.x(), track_rect.y(), progress_width, track_height)
        
        painter.setBrush(QColor("#44aa66")) 
        painter.drawRoundedRect(progress_rect, 4, 4)
        
        # Draw Handle (Teardrop shape)
        handle_x = track_rect.x() + progress_width
        handle_width = 16 # Wider for teardrop
        handle_height = 24
        
        cy = rect.center().y()
        
        # Create Teardrop Path (Pointing Down)
        path = QPainterPath()
        radius = handle_width / 2
        top_cy = cy - (handle_height / 2) + radius
        
        path.moveTo(handle_x - radius, top_cy)
        path.arcTo(QRectF(handle_x - radius, top_cy - radius, handle_width, handle_width), 180, -180)
        path.lineTo(handle_x, cy + (handle_height / 2))
        path.lineTo(handle_x - radius, top_cy)
        path.closeSubpath()

        painter.setBrush(QColor("#cccccc")) 
        painter.setPen(Qt.NoPen)
        painter.drawPath(path)
        
        painter.setPen(QPen(QColor(0, 0, 0, 80), 1))

        line_top = top_cy - radius + 4
        line_bottom = top_cy + radius - 4
        painter.drawLine(handle_x, line_top, handle_x, line_bottom)

    # Mouse events for jump-to-click
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            val_range = self.maximum() - self.minimum()
            margin = 10
            track_width = self.width() - 2 * margin
            if track_width > 0:
                click_x = event.pos().x() - margin
                ratio = max(0.0, min(1.0, click_x / track_width))
                new_val = self.minimum() + int(ratio * val_range)
                self.is_user_interacting = True # Flag BEFORE value change to allow emit
                self.setValue(new_val)
        
        super().mousePressEvent(event)
        
    def mouseMoveEvent(self, event):
         if event.buttons() & Qt.LeftButton:
            val_range = self.maximum() - self.minimum()
            margin = 10
            track_width = self.width() - 2 * margin
            if track_width > 0:
                click_x = event.pos().x() - margin
                ratio = max(0.0, min(1.0, click_x / track_width))
                new_val = self.minimum() + int(ratio * val_range)
                self.is_user_interacting = True
                self.setValue(new_val)
         super().mouseMoveEvent(event)
