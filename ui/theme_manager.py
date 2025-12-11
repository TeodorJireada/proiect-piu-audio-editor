import os
from PySide6.QtGui import QPalette, QColor
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

class ThemeManager:
    @staticmethod
    def get_saved_theme():
        settings = QSettings("PyDAW", "AudioEditor")
        return settings.value("theme", "dark")

    @staticmethod
    def save_theme(theme_name):
        settings = QSettings("PyDAW", "AudioEditor")
        settings.setValue("theme", theme_name)

    @staticmethod
    def apply_theme(app, theme_name=None):
        """
        Applies consistency styles (Fusion) and loads the requested theme QSS and Palette.
        If theme_name is None, loads from settings.
        """
        if theme_name is None:
            theme_name = ThemeManager.get_saved_theme()
            
        app.setStyle("Fusion")
        
        # Apply Palette
        if theme_name == "dark":
            palette = ThemeManager._get_dark_palette()
        elif theme_name == "high_contrast":
            palette = ThemeManager._get_high_contrast_palette()
        else:
            # Fallback
            palette = ThemeManager._get_dark_palette()
            
        app.setPalette(palette)
        
        # Load QSS
        qss_path = os.path.join("assets", "themes", f"{theme_name}.qss")
        if os.path.exists(qss_path):
            with open(qss_path, "r") as f:
                app.setStyleSheet(f.read())
        else:
            print(f"Theme file not found: {qss_path}")

    @staticmethod
    def _get_dark_palette():
        palette = QPalette()
        
        # Base Colors
        window_color = QColor(43, 43, 43)      # #2b2b2b
        window_text = QColor(224, 224, 224)    # #e0e0e0
        base_color = QColor(32, 32, 32)        # #202020
        alternate_base = QColor(43, 43, 43)    # #2b2b2b
        text_color = QColor(224, 224, 224)
        button_color = QColor(60, 60, 60)      # #3c3c3c (adjusted slightly lighter for base button)
        button_text = QColor(224, 224, 224)
        highlight = QColor(85, 119, 204)       # #5577cc
        highlight_text = QColor(255, 255, 255)
        
        # Set Palette Roles
        palette.setColor(QPalette.Window, window_color)
        palette.setColor(QPalette.WindowText, window_text)
        palette.setColor(QPalette.Base, base_color)
        palette.setColor(QPalette.AlternateBase, alternate_base)
        palette.setColor(QPalette.ToolTipBase, window_color)
        palette.setColor(QPalette.ToolTipText, window_text)
        palette.setColor(QPalette.Text, text_color)
        palette.setColor(QPalette.Button, button_color)
        palette.setColor(QPalette.ButtonText, button_text)
        palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.Link, highlight)
        palette.setColor(QPalette.Highlight, highlight)
        palette.setColor(QPalette.HighlightedText, highlight_text)
        
        # Disabled states
        palette.setColor(QPalette.Disabled, QPalette.Text, QColor(127, 127, 127))
        palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(127, 127, 127))
        
        
        return palette

    @staticmethod
    def _get_high_contrast_palette():
        palette = QPalette()
        
        # High Contrast: Black & White & Cyan/Yellow
        black = QColor(0, 0, 0)
        white = QColor(255, 255, 255)
        cyan = QColor(0, 255, 255)
        
        palette.setColor(QPalette.Window, black)
        palette.setColor(QPalette.WindowText, white)
        palette.setColor(QPalette.Base, black)
        palette.setColor(QPalette.AlternateBase, black)
        palette.setColor(QPalette.ToolTipBase, black)
        palette.setColor(QPalette.ToolTipText, white)
        palette.setColor(QPalette.Text, white)
        palette.setColor(QPalette.Button, black)
        palette.setColor(QPalette.ButtonText, white)
        palette.setColor(QPalette.BrightText, cyan)
        palette.setColor(QPalette.Link, cyan)
        palette.setColor(QPalette.Highlight, cyan)
        palette.setColor(QPalette.HighlightedText, black)
        
        # Disabled
        palette.setColor(QPalette.Disabled, QPalette.Text, QColor(128, 128, 128))
        palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(128, 128, 128))
        
        return palette
