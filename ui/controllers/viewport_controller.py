from PySide6.QtCore import QObject, Qt, QTimer, QEvent
from PySide6.QtWidgets import QScrollBar, QStyle

class ViewportController(QObject):
    def __init__(self, main_window):
        super().__init__()
        self.mw = main_window
        self.timeline = main_window.timeline
        self.right_scroll = main_window.right_scroll
        self.left_scroll = main_window.left_scroll
        self.timeline_scroll = main_window.timeline_scroll
        self.h_scrollbar = main_window.h_scrollbar
        self.track_manager = main_window.track_manager
        
        self.scroll_timer = QTimer()
        self.scroll_timer.setInterval(30)
        self.scroll_timer.timeout.connect(self.check_edge_scroll)

        # Connect Timeline signals
        self.timeline.zoom_request.connect(self.perform_zoom)
        self.timeline.drag_started.connect(self.handle_drag_started)
        self.timeline.drag_finished.connect(self.handle_drag_finished)
        self.timeline.position_changed.connect(self.user_seek)

        # Sync Scrollbars
        self.setup_sync_scrollbars()

    def setup_sync_scrollbars(self):
        # Vertical Sync: Left Scroll <-> Right Scroll
        self.left_scroll.verticalScrollBar().valueChanged.connect(
            self.right_scroll.verticalScrollBar().setValue
        )
        self.right_scroll.verticalScrollBar().valueChanged.connect(
            self.left_scroll.verticalScrollBar().setValue
        )
        
        # Horizontal Sync: Top HBuffer <-> Timeline Scroll <-> Right Scroll
        def sync_h(val):
            if self.timeline_scroll.horizontalScrollBar().value() != val:
                self.timeline_scroll.horizontalScrollBar().setValue(val)
            if self.right_scroll.horizontalScrollBar().value() != val:
                self.right_scroll.horizontalScrollBar().setValue(val)
            if self.h_scrollbar.value() != val:
                self.h_scrollbar.setValue(val)
                
        self.h_scrollbar.valueChanged.connect(sync_h)
        self.timeline_scroll.horizontalScrollBar().valueChanged.connect(sync_h)
        self.right_scroll.horizontalScrollBar().valueChanged.connect(sync_h)
        
        # Sync Ranges
        def update_range(min_val, max_val):
             self.h_scrollbar.setRange(min_val, max_val)
             self.h_scrollbar.setPageStep(self.right_scroll.horizontalScrollBar().pageStep())
             
        self.right_scroll.horizontalScrollBar().rangeChanged.connect(update_range)

    def calculate_min_zoom(self):
        viewport_width = self.right_scroll.viewport().width()
        if viewport_width <= 50: viewport_width = 800 
        
        duration = getattr(self.timeline, 'duration', 60)
        if duration <= 0.1: duration = 1.0
        
        return viewport_width / duration

    def zoom_to_fit(self):
        max_duration = 0
        for track in self.mw.audio.tracks:
            for clip in track.clips:
                end = clip.start_time + clip.duration
                if end > max_duration: max_duration = end
        
        if max_duration <= 0: max_duration = 60
        
        available_width = self.right_scroll.viewport().width() - 50
        if available_width <= 0: available_width = 800
        
        required_pps = available_width / max_duration
        
        min_zoom = self.calculate_min_zoom()
        required_pps = max(min_zoom, min(1000.0, required_pps))
        
        self.timeline.set_zoom(required_pps)
        self.update_zoom(required_pps)
        self.right_scroll.horizontalScrollBar().setValue(0)

    def update_zoom(self, px_per_sec):
        self.track_manager.update_zoom(px_per_sec)
        
        current_time = self.mw.audio.get_playhead_time()
        x_pixel = current_time * px_per_sec
        self.update_playhead_visuals(x_pixel, scroll_to_view=False)

    def perform_zoom_step(self, direction):
        viewport_width = self.right_scroll.viewport().width()
        center_x_screen = viewport_width / 2
        
        current_scroll = self.right_scroll.horizontalScrollBar().value()
        current_zoom = self.timeline.pixels_per_second
        
        absolute_x = current_scroll + center_x_screen
        time_at_center = absolute_x / current_zoom
        
        if direction > 0:
            new_zoom = current_zoom * 1.5
        else:
            new_zoom = current_zoom / 1.5
        
        min_zoom = self.calculate_min_zoom()
        new_zoom = max(min_zoom, min(1000.0, new_zoom))
        
        if new_zoom == current_zoom: return

        self.timeline.set_zoom(new_zoom)
        self.update_zoom(new_zoom)
        
        new_absolute_x = time_at_center * new_zoom
        new_scroll = int(new_absolute_x - center_x_screen)
        
        self.right_scroll.horizontalScrollBar().setValue(new_scroll)

    def perform_zoom(self, delta, global_pos):
        viewport_pos = self.right_scroll.viewport().mapFromGlobal(global_pos.toPoint())
        mouse_x_screen = viewport_pos.x()
        
        current_scroll = self.right_scroll.horizontalScrollBar().value()
        current_zoom = self.timeline.pixels_per_second
        
        absolute_x = current_scroll + mouse_x_screen
        time_under_mouse = absolute_x / current_zoom
        
        if delta > 0:
            new_zoom = current_zoom * 1.5
        else:
            new_zoom = current_zoom / 1.5
        
        min_zoom = self.calculate_min_zoom()
        new_zoom = max(min_zoom, min(1000.0, new_zoom))
        
        if new_zoom == current_zoom: return

        self.timeline.set_zoom(new_zoom)
        self.update_zoom(new_zoom)
        
        new_absolute_x = time_under_mouse * new_zoom
        new_scroll = int(new_absolute_x - mouse_x_screen)
        
        self.right_scroll.horizontalScrollBar().setValue(new_scroll)

    def handle_drag_started(self):
        self.scroll_timer.start()

    def handle_drag_finished(self):
        self.scroll_timer.stop()

    def check_edge_scroll(self):
        global_mouse = self.mw.cursor().pos()
        viewport = self.timeline_scroll.viewport()
        mouse_pos = viewport.mapFromGlobal(global_mouse)
        
        scroll_margin = 50
        scroll_step = 20
        
        current_scroll = self.right_scroll.horizontalScrollBar().value()
        viewport_width = viewport.width()
        
        new_scroll = current_scroll
        
        if mouse_pos.x() > viewport_width - scroll_margin:
            new_scroll += scroll_step
        elif mouse_pos.x() < scroll_margin:
            new_scroll -= scroll_step
        
        if new_scroll != current_scroll:
            new_scroll = max(0, new_scroll)
            self.right_scroll.horizontalScrollBar().setValue(new_scroll)
            
            new_absolute_x = new_scroll + mouse_pos.x()
            new_absolute_x = max(0, new_absolute_x)
            
            self.user_seek(new_absolute_x)

    def user_seek(self, x_pixels):
        if hasattr(self.timeline, 'is_dragging') and self.timeline.is_dragging:
             viewport_start = self.right_scroll.horizontalScrollBar().value()
             viewport_end = viewport_start + self.right_scroll.viewport().width()
             x_pixels = max(viewport_start, min(x_pixels, viewport_end))

        time_sec = x_pixels / self.timeline.pixels_per_second
        
        self.mw.edit_cursor_time = time_sec
        self.timeline.set_cursor(x_pixels)
        
        self.mw.audio.set_playhead(x_pixels, px_per_second=self.timeline.pixels_per_second)
        self.update_playhead_visuals(x_pixels, scroll_to_view=False)

    def update_playhead_visuals(self, x, scroll_to_view=False):
        self.timeline.set_playhead(x)
        self.track_manager.update_playhead_visuals(x)
        
        current_time = x / self.timeline.pixels_per_second
        self.mw.ribbon.update_playhead_position(current_time, self.timeline.duration)
            
        if scroll_to_view:
             viewport_width = self.right_scroll.viewport().width()
             current_scroll = self.right_scroll.horizontalScrollBar().value()
             
             if x > current_scroll + viewport_width:
                 target_scroll = x
                 self.right_scroll.horizontalScrollBar().setValue(int(target_scroll))
             elif x < current_scroll:
                 target_scroll = max(0, x - viewport_width + 50) # Page back, keeping playhead near right edge
                 self.right_scroll.horizontalScrollBar().setValue(int(target_scroll))
