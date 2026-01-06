import os
from PySide6.QtCore import QObject, QTimer
from PySide6.QtWidgets import QFileDialog, QMessageBox

class ProjectIO(QObject):
    def __init__(self, main_window):
        super().__init__()
        self.mw = main_window
        self.project_manager = main_window.project_manager
        self.track_manager = main_window.track_manager
        self.undo_stack = main_window.undo_stack
        
        self.current_project_path = None
        self.clean_command = None

        # Signals
        self.undo_stack.stack_changed.connect(self.update_dirty_state)

    def on_new_project(self):
        if not self.check_save_changes():
            return
            
        self.track_manager.clear_all_tracks()
        self.undo_stack.clear()
        self.current_project_path = None
        self.clean_command = None
        self.update_dirty_state()

    def on_open_project(self):
        if not self.check_save_changes():
            return

        file_path, _ = QFileDialog.getOpenFileName(self.mw, "Open Project", "", "Project Files (*.pydaw)")
        if file_path:
            self.track_manager.load_project(file_path)
            self.current_project_path = file_path
            self.undo_stack.clear()
            self.clean_command = None
            self.update_dirty_state()

    def on_save_project(self):
        if self.current_project_path:
            success = self.project_manager.save_project(self.current_project_path, self.mw.audio)
            if success:
                self.mw.ribbon.show_loading(f"Saved to {os.path.basename(self.current_project_path)}")
                QTimer.singleShot(2000, self.mw.ribbon.hide_loading)
                self.clean_command = self.undo_stack.current_command
                self.update_dirty_state()
            else:
                QMessageBox.critical(self.mw, "Error", "Failed to save project.")
        else:
            self.on_save_project_as()

    def on_save_project_as(self):
        file_path, _ = QFileDialog.getSaveFileName(self.mw, "Save Project As", "", "Project Files (*.pydaw)")
        if file_path:
            if not file_path.endswith(".pydaw"):
                file_path += ".pydaw"
            
            self.current_project_path = file_path
            success = self.project_manager.save_project(file_path, self.mw.audio)
            
            if success:
                self.mw.setWindowTitle(f"Python Qt DAW - {os.path.basename(file_path)}")
                QMessageBox.information(self.mw, "Success", f"Project saved to {file_path}")
                self.clean_command = self.undo_stack.current_command
                self.update_dirty_state()
            else:
                QMessageBox.critical(self.mw, "Error", "Failed to save project.")

    def on_export_audio(self):
        file_path, _ = QFileDialog.getSaveFileName(self.mw, "Export Audio", "", "WAV Files (*.wav)")
        if file_path:
            if not file_path.endswith(".wav"):
                file_path += ".wav"
            
            duration = self.mw.timeline.duration
            max_end = 0
            for track in self.mw.audio.tracks:
                for clip in track.clips:
                    end = clip.start_time + clip.duration
                    if end > max_end: max_end = end
            
            if max_end == 0:
                QMessageBox.warning(self.mw, "Warning", "Project is empty.")
                return

            export_duration = max_end + 1.0
            self.mw.audio.export_audio(file_path, export_duration)
            QMessageBox.information(self.mw, "Success", f"Audio exported to {file_path}")

    def check_save_changes(self):
        is_dirty = self.undo_stack.current_command != self.clean_command
        if not is_dirty:
            return True
            
        reply = QMessageBox.question(
            self.mw, 
            "Unsaved Changes", 
            "You have unsaved changes. Do you want to save them?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
        )
        
        if reply == QMessageBox.Save:
            self.on_save_project()
            return self.undo_stack.current_command == self.clean_command
        elif reply == QMessageBox.Discard:
            return True
        else:
            return False

    def update_dirty_state(self):
        is_dirty = self.undo_stack.current_command != self.clean_command
        
        title = "Python Qt DAW"
        if self.current_project_path:
            title += f" - {os.path.basename(self.current_project_path)}"
        else:
            title += " - Untitled"
            
        if is_dirty:
            title = "* " + title
            
        self.mw.setWindowTitle(title)
