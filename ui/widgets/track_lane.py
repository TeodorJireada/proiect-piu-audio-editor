from PySide6.QtCore import Qt, QRect, Signal, QPointF
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QPolygonF, QPalette, QCursor, QFont
import numpy as np
import os
from PySide6.QtWidgets import QFrame, QApplication

class TrackLane(QFrame):
    clip_moved = Signal(int, float, float) 
    clip_trimmed = Signal(int, float, float, float, float, float, float) 
    clip_split = Signal(int, float) 
    clip_duplicated = Signal(int, float) 
    clip_deleted = Signal(int)
    clip_selected = Signal(int) # Emits index immediately on click
    paste_requested = Signal(float) # Emits time on empty click
    
    def __init__(self):
        super().__init__()
        self.setObjectName("TrackLane")
        self.setFixedHeight(80)
        self.setMinimumWidth(3000)
        self.clips = [] 
        self.playhead_x = 0
        self.pixels_per_second = 10
        self.duration = 60
        self.is_placeholder = False
        self.snap_enabled = False
        self.bpm = 120
        
        # Dragging State
        self.dragging_clip_index = -1
        self.drag_mode = None 
        self.drag_start_x = 0
        self.clip_initial_start_time = 0.0
        self.clip_initial_duration = 0.0
        self.clip_initial_offset = 0.0
        
        self.HANDLE_WIDTH = 10

        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.active_tool = "MOVE"
        self.selected_clip_index = -1

    def set_selection(self, index):
        self.selected_clip_index = index
        self.update()

    def get_snapped_time(self, time):
        if not self.snap_enabled:
            return time
        
        beat_duration = 60.0 / self.bpm
        snap_interval = beat_duration / 4.0 # 1/4 beat
        return round(time / snap_interval) * snap_interval

    def set_tool(self, tool_name):
        self.active_tool = tool_name
        self.update()

    def set_zoom(self, px_per_sec):
        self.pixels_per_second = px_per_sec
        self.update_width()
        self.update()

    def set_duration(self, duration):
        self.duration = duration
        self.update_width()
        self.update()

    def set_snap_enabled(self, enabled):
        self.snap_enabled = enabled

    def set_bpm(self, bpm):
        self.bpm = bpm

    def update_width(self):
        width = int(self.duration * self.pixels_per_second)
        self.setMinimumWidth(width)

    def clear_clips(self):
        self.clips = []
        self.update()

    def add_clip(self, name, start_time, duration, start_offset, color, waveform=None, data=None, sample_rate=44100):
        self.clips.append({
            "name": name,
            "start_time": start_time,
            "duration": duration,
            "start_offset": start_offset,
            "color": color,
            "waveform": waveform,
            "data": data,
            "sample_rate": sample_rate
        })
        self.update()

    def update_clip(self, clip_index, start_time, duration, start_offset=None):
        if 0 <= clip_index < len(self.clips):
            self.clips[clip_index]['start_time'] = start_time
            self.clips[clip_index]['duration'] = duration
            if start_offset is not None:
                self.clips[clip_index]['start_offset'] = start_offset
            self.update()

    def set_clip_start_time(self, clip_index, start_time):
        if 0 <= clip_index < len(self.clips):
            self.clips[clip_index]['start_time'] = start_time
            self.update()

    def update_color(self, new_color):
        for clip in self.clips:
            clip['color'] = new_color
        self.update()

    def set_playhead(self, x):
        self.playhead_x = x
        self.update()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Shift:
            self.setCursor(Qt.CrossCursor)
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Shift:
            # Refresh cursor state by triggering a move logic check
            pos = self.mapFromGlobal(QCursor.pos())
            self._update_cursor_at(pos)
        super().keyReleaseEvent(event)

    def mousePressEvent(self, event):
        if self.is_placeholder: return
        
        if event.button() == Qt.LeftButton:
            click_x = event.position().x()
            
            # Check if clicked on a clip
            clicked_clip_index = -1
            for i, clip in enumerate(self.clips):
                start_x = int(clip['start_time'] * self.pixels_per_second)
                width = int(clip['duration'] * self.pixels_per_second)
                end_x = start_x + width
                
                if start_x <= click_x <= end_x:
                    clicked_clip_index = i
                    break
            
            if clicked_clip_index != -1:
                # Handle Clip Click

                # Shift+Click to Split
                if event.modifiers() & Qt.ShiftModifier:
                    self.handle_split(clicked_clip_index, click_x)
                    return

                if self.active_tool == "SPLIT":
                    self.handle_split(clicked_clip_index, click_x)
                    return
                elif self.active_tool == "DUPLICATE":
                    self.handle_duplicate(clicked_clip_index)
                    return
                elif self.active_tool == "DELETE":
                    self.handle_delete(clicked_clip_index)
                    return
                
                # MOVE TOOL & COPY LOGIC
                # Always emit selection on click
                self.clip_selected.emit(clicked_clip_index)

                self.dragging_clip_index = clicked_clip_index
                self.drag_start_x = click_x
                clip = self.clips[clicked_clip_index]
                self.clip_initial_start_time = clip['start_time']
                self.clip_initial_duration = clip['duration']
                self.clip_initial_offset = clip['start_offset']
                
                # Check for handles
                start_x = int(clip['start_time'] * self.pixels_per_second)
                width = int(clip['duration'] * self.pixels_per_second)
                end_x = start_x + width

                if click_x < start_x + self.HANDLE_WIDTH:
                    self.drag_mode = "TRIM_LEFT"
                elif click_x > end_x - self.HANDLE_WIDTH:
                    self.drag_mode = "TRIM_RIGHT"
                else:
                    self.drag_mode = "MOVE"
                
            else:
                # Handle Empty Space Click
                if self.active_tool == "MOVE":
                    time = click_x / self.pixels_per_second
                    snapped_time = self.get_snapped_time(time)
                    self.paste_requested.emit(snapped_time)

        elif event.button() == Qt.RightButton:
            click_x = event.position().x()
            
            # Check if clicked on a clip
            clicked_clip_index = -1
            for i, clip in enumerate(self.clips):
                start_x = int(clip['start_time'] * self.pixels_per_second)
                width = int(clip['duration'] * self.pixels_per_second)
                end_x = start_x + width
                
                if start_x <= click_x <= end_x:
                    clicked_clip_index = i
                    break
            
            if clicked_clip_index != -1:
                self.handle_delete(clicked_clip_index)

    def mouseMoveEvent(self, event):
        current_x = event.position().x()
        
        if self.dragging_clip_index != -1:
            delta_x = current_x - self.drag_start_x
            delta_time = delta_x / self.pixels_per_second
            
            clip = self.clips[self.dragging_clip_index]
            
            if self.drag_mode == "MOVE":
                new_start_time = self.clip_initial_start_time + delta_time
                if new_start_time < 0: new_start_time = 0
                
                # Snapping Logic
                new_start_time = self.get_snapped_time(new_start_time)

                clip['start_time'] = new_start_time
                
            elif self.drag_mode == "TRIM_LEFT":
                
                new_start_time = self.clip_initial_start_time + delta_time
                
                # Check bounds
                if new_start_time < 0: new_start_time = 0
                
                # Calculate new offset
                new_offset = self.clip_initial_offset + (new_start_time - self.clip_initial_start_time)
                
                if new_offset < 0:
                    new_offset = 0
                    new_start_time = self.clip_initial_start_time - self.clip_initial_offset
                
                # Calculate new duration
                end_time = self.clip_initial_start_time + self.clip_initial_duration
                new_duration = end_time - new_start_time
                
                if new_duration < 0.1: # Minimum duration
                    new_duration = 0.1
                    new_start_time = end_time - 0.1
                    new_offset = self.clip_initial_offset + (new_start_time - self.clip_initial_start_time)

                clip['start_time'] = new_start_time
                clip['duration'] = new_duration
                clip['start_offset'] = new_offset

            elif self.drag_mode == "TRIM_RIGHT":
                new_duration = self.clip_initial_duration + delta_time
                if new_duration < 0.1: new_duration = 0.1
                
                clip['duration'] = new_duration

            self.update()
            
        else:
            self._update_cursor_at(event.position())

    def _update_cursor_at(self, pos):
        current_x = pos.x()
        modifiers = QApplication.keyboardModifiers()
        
        # Hover Logic
        hover_cursor = Qt.ArrowCursor
        
        # Check Modifiers for Split (Shift)
        if modifiers & Qt.ShiftModifier:
            hover_cursor = Qt.CrossCursor
        elif self.active_tool == "SPLIT":
            hover_cursor = Qt.CrossCursor
        elif self.active_tool == "DUPLICATE":
            hover_cursor = Qt.DragCopyCursor
        elif self.active_tool == "DELETE":
            hover_cursor = Qt.ForbiddenCursor
        
        # Only check handles if MOVE tool and Shift not held
        if self.active_tool == "MOVE" and not (modifiers & Qt.ShiftModifier):
            for clip in self.clips:
                start_x = int(clip['start_time'] * self.pixels_per_second)
                width = int(clip['duration'] * self.pixels_per_second)
                end_x = start_x + width
                
                if start_x <= current_x <= end_x:
                    if current_x < start_x + self.HANDLE_WIDTH:
                        hover_cursor = Qt.SizeHorCursor
                    elif current_x > end_x - self.HANDLE_WIDTH:
                        hover_cursor = Qt.SizeHorCursor
                    else:
                        hover_cursor = Qt.ArrowCursor 
                    break
        
        self.setCursor(hover_cursor)

    def mouseReleaseEvent(self, event):
        if self.dragging_clip_index != -1:
            if event.button() == Qt.LeftButton:
                clip = self.clips[self.dragging_clip_index]
                
                if self.drag_mode == "MOVE":
                    final_start_time = clip['start_time']
                    if abs(final_start_time - self.clip_initial_start_time) > 0.001:
                        self.clip_moved.emit(self.dragging_clip_index, self.clip_initial_start_time, final_start_time)
                
                elif self.drag_mode in ["TRIM_LEFT", "TRIM_RIGHT"]:
                    self.clip_trimmed.emit(
                        self.dragging_clip_index,
                        self.clip_initial_start_time,
                        self.clip_initial_duration,
                        self.clip_initial_offset,
                        clip['start_time'],
                        clip['duration'],
                        clip['start_offset']
                    )

                self.dragging_clip_index = -1
                self.drag_mode = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        palette = self.palette()
        
        # Draw Clips
        mid_y = self.height() / 2 
        
        for i, clip in enumerate(self.clips):
            start_x = int(clip['start_time'] * self.pixels_per_second)
            width = int(clip['duration'] * self.pixels_per_second)
            
            # Draw Clip Background
            # Top border 1px lower to be visible
            clip_rect = QRect(start_x, 1, width, self.height() - 2)
            
            # Use Palette for base background of clip? 
            # Actually clips are usually colored distinctively. 
            # But let's use AlternateBase if we wanted theme compliance, 
            # though here we have custom clip colors.
            # We'll stick to a dark background that matches the theme "Button" or "Base"
            # But wait, clips have transparency? 
            # The previous code used QColor(30, 30, 40) which is very close to Base/Window.
            # Let's use QPalette.Button for the clip body background if opaque.
            
            # Use clip color, but maybe darken it for background?
            # Or use Theme Base.
            painter.setBrush(QBrush(palette.color(QPalette.AlternateBase))) 
            
            # Determine Color (Highlight if selected)
            base_color = QColor(clip['color'])
            if i == self.selected_clip_index:
                painter.setPen(base_color.lighter(150)) # Lighter border
            else:
                painter.setPen(base_color)        
            
            painter.drawRoundedRect(clip_rect, 6, 6) # Rounded corners

            # DRAW WAVEFORM
            if clip['waveform'] is not None:
                wave_color = QColor(clip['color'])
                if i == self.selected_clip_index:
                    wave_color = wave_color.lighter(130) # Lighten waveform too
                
                # Fill Color
                fill_color = QColor(wave_color)
                fill_color.setAlpha(100) # Semi-transparent fill
                
                # Stroke Color
                stroke_color = QColor(wave_color)
                stroke_color.setAlpha(255) # Opaque stroke

                waveform = clip['waveform']
                original_sps = 100 

                # View Culling: Determine visible range
                view_min_x = event.rect().left()
                view_max_x = event.rect().right()
                
                # Clip bounds in widget coordinates
                clip_min_x = start_x
                clip_max_x = start_x + width
                
                # Intersection
                draw_start_x = max(view_min_x, clip_min_x)
                draw_end_x = min(view_max_x, clip_max_x)
                
                if draw_start_x < draw_end_x:
                     points_top = []
                     points_bottom = []
                     if clip.get('waveform') is not None:
                         waveform = clip['waveform']
                         
                         clip_offset = clip['start_offset']
                         
                         step = 2
                         delta = int(draw_start_x - start_x)
                         k = (delta + step - 1) // step if delta > 0 else 0 
                         aligned_start_x = int(start_x + k * step)
                         
                         for x_screen in range(aligned_start_x, int(draw_end_x), step): 
                             t = (x_screen - start_x) / self.pixels_per_second + clip_offset
                             wf_idx = int(t * original_sps)
                             
                             if 0 <= wf_idx < len(waveform):
                                 val = float(waveform[wf_idx])
                                 
                                 # Top 
                                 y_top = mid_y - (val * 35)
                                 points_top.append(QPointF(x_screen, y_top))
                                 
                                 # Bottom
                                 y_bottom = mid_y + (val * 35)
                                 points_bottom.append(QPointF(x_screen, y_bottom))

                     if points_top and points_bottom:
                         # Create Polygon for Fill
                         # Top points (Left -> Right) + Bottom points (Right -> Left)
                         fill_poly = QPolygonF()
                         for p in points_top:
                             fill_poly.append(p)
                         for p in reversed(points_bottom):
                             fill_poly.append(p)
                         
                         # Close the loop
                         fill_poly.append(points_top[0])

                         painter.setBrush(QBrush(fill_color))
                         painter.setPen(Qt.NoPen)
                         painter.drawPolygon(fill_poly)

                         # Draw Strokes (Outline)
                         painter.setBrush(Qt.NoBrush)
                         painter.setPen(QPen(stroke_color, 1))
                         painter.drawPolyline(points_top)
                         painter.drawPolyline(points_bottom)

            # Draw Clip Name Overlay
            painter.setPen(palette.color(QPalette.Text))
            display_name = os.path.basename(clip['name'])
            painter.drawText(clip_rect.adjusted(5, 5, 0, 0), Qt.AlignLeft | Qt.AlignTop, display_name)

        # Draw Playhead
        # Use Highlight color but make it opaque/solid?
        playhead_color = palette.color(QPalette.BrightText) # Usually Red or bright in dark themes
        # If BrightText is not red enough, fallback to Highlight?
        # ThemeManager sets BrightText to Red (255,0,0). Perfect.
        painter.setPen(QPen(playhead_color, 1))
        
        painter.drawLine(QPointF(self.playhead_x, 0), QPointF(self.playhead_x, self.height()))

    def contextMenuEvent(self, event):
        pass # Disable context menu

    def handle_split(self, clip_index, click_x):
        split_time = click_x / self.pixels_per_second
        self.clip_split.emit(clip_index, split_time)

    def handle_duplicate(self, clip_index):
        if 0 <= clip_index < len(self.clips):
            clip = self.clips[clip_index]
            new_start = clip['start_time'] + clip['duration']
            self.clip_duplicated.emit(clip_index, new_start)

    def handle_delete(self, clip_index):
        self.clip_deleted.emit(clip_index)