from PySide6.QtWidgets import QSlider, QStyle, QStyleOptionSlider, QMenu
from PySide6.QtGui import QPainter, QBrush, QColor, QPen, QPainterPath, QPalette, QAction
from PySide6.QtCore import Qt, QRectF

class ModernSlider(QSlider):
    def __init__(self, orientation=Qt.Horizontal, parent=None, default_value=100):
        super().__init__(orientation, parent)
        self.setMouseTracking(True)
        self.setMinimumHeight(24) # Ensure enough vertical space for handle
        self.meter_level = 0.0 # 0.0 to 1.0
        self.default_value = default_value

    def set_meter_level(self, level):
        self.meter_level = max(0.0, min(1.0, level))
        self.update()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        reset_action = QAction("Reset", self)
        reset_action.triggered.connect(self.reset_to_default)
        menu.addAction(reset_action)
        menu.exec(event.globalPos())

    def reset_to_default(self):
        if self.value() != self.default_value:
             self.sliderPressed.emit() # Simulate start of interaction
             self.setValue(self.default_value)
             self.sliderReleased.emit() # Simulate end of interaction

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        palette = self.palette()

        # Get geometric info
        opt = QStyleOptionSlider()
        self.initStyleOption(opt)
        
        rect = self.rect()
        
        # Dimensions
        margin = 4
        if self.orientation() == Qt.Horizontal:
            track_height = 6 # Slightly thinner track
            handle_width = 6 # Narrower handle
            handle_height = 16 # Taller handle
            
            # Center vertically
            track_y = rect.center().y() - (track_height / 2)
            track_rect = QRectF(margin, track_y, rect.width() - 2 * margin, track_height)
            
            # Calculate handle position
            val_range = self.maximum() - self.minimum()
            if val_range == 0:
                pos_ratio = 0
            else:
                pos_ratio = (self.value() - self.minimum()) / val_range
                
            available_width = track_rect.width() - handle_width
            handle_x = track_rect.x() + (pos_ratio * available_width)
            handle_y = rect.center().y() - (handle_height / 2)
            
            handle_rect = QRectF(handle_x, handle_y, handle_width, handle_height)
            
            # Draw Continuous Track Background (Inactive part)
            # We draw the full track first, so there is no "transparency" behind the handle or gaps.
            painter.setPen(Qt.NoPen)
            # Use Window color darkened
            painter.setBrush(palette.color(QPalette.Window).darker(150))
            painter.drawRoundedRect(track_rect, 3, 3)
            
            # Draw Meter / Active Track
            # The bar starts from left and goes up to meter_level.
            
            # Map meter level to pixels
            if track_rect.width() > 0:
                 meter_pixel_width = self.meter_level * track_rect.width()
                 
                 # Define the "Gap" point relative to the handle
                 # The Meter should stop 'gap' pixels before the handle STARTS.
                 gap = 3
                 active_limit_x = handle_x - gap
                 
                 # Calculate where the meter would naturally end
                 natural_meter_end_x = track_rect.x() + meter_pixel_width
                 
                 # Clip the meter to the gap if it exceeds it
                 # If the meter is lower than the gap, it ends naturally.
                 # If the meter is higher (audio peaking), we visually clamp it to the gap (or just let it hit the gap flatly).
                 
                 draw_end_x = min(natural_meter_end_x, active_limit_x)
                 
                 if draw_end_x > track_rect.x():
                     painter.setBrush(QColor("#44aa66")) # Green (Semantic)
                     
                     start_x = track_rect.left()
                     end_x = draw_end_x
                     
                     # Check if we are touching the gap limit (implies flat end needed)
                     # or if we are just drawing a short bar (rounded end)
                     is_clamped_at_gap = (abs(draw_end_x - active_limit_x) < 2)
                     
                     if is_clamped_at_gap:
                         # Flat End
                         path_meter = QPainterPath()
                         path_meter.moveTo(end_x, track_y) # Top Right
                         path_meter.lineTo(start_x + 3, track_y)
                         path_meter.arcTo(start_x, track_y, 6, 6, 90, 90)
                         path_meter.lineTo(start_x, track_y + track_height - 3)
                         path_meter.arcTo(start_x, track_y + track_height - 6, 6, 6, 180, 90)
                         path_meter.lineTo(end_x, track_y + track_height) # Bottom Right
                         path_meter.lineTo(end_x, track_y) # Close
                         painter.drawPath(path_meter)
                     else:
                         # Rounded End (standard rounded rect behavior)
                         # BUT, the left side must match the track's rounded start.
                         # drawRoundedRect handles corners symmetrically.
                         # Since the track has radius 3, and we draw inside it, using radius 3 is fine.
                         painter.drawRoundedRect(QRectF(start_x, track_y, end_x - start_x, track_height), 3, 3)
            
        else:
            # Vertical Slider (if needed later)
            track_width = 8
            handle_width = 14
            handle_height = 14
            
            track_x = rect.center().x() - (track_width / 2)
            track_rect = QRectF(track_x, margin, track_width, rect.height() - 2 * margin)
            
            # Calculate handle position
            val_range = self.maximum() - self.minimum()
            if val_range == 0:
                pos_ratio = 0
            else:
                pos_ratio = (self.value() - self.minimum()) / val_range
            
            pass 

        # Draw Handle
        # Use ButtonText color (usually white/bright in dark themes)
        painter.setBrush(palette.color(QPalette.ButtonText))
        painter.setPen(Qt.NoPen)
        # Full rounded capsule shape (Radius = half width)
        # Since width 6, radius 3.
        painter.drawRoundedRect(handle_rect, 3, 3)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Jump to click position immediately
            # Calculate value from click position
            if self.orientation() == Qt.Horizontal:
                val_range = self.maximum() - self.minimum()
                margin = 4
                handle_width = 6
                track_width = self.width() - 2 * margin - handle_width
                
                click_x = event.pos().x() - margin - (handle_width / 2)
                ratio = max(0, min(1, click_x / track_width))
                new_val = self.minimum() + (ratio * val_range)
                self.setValue(int(new_val))
                event.accept()
                
            self.sliderPressed.emit()
        
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
             if self.orientation() == Qt.Horizontal:
                val_range = self.maximum() - self.minimum()
                margin = 4
                handle_width = 6
                track_width = self.width() - 2 * margin - handle_width
                
                click_x = event.pos().x() - margin - (handle_width / 2)
                ratio = max(0, min(1, click_x / track_width))
                new_val = self.minimum() + (ratio * val_range)
                self.setValue(int(new_val))
                event.accept()
        super().mouseMoveEvent(event)
