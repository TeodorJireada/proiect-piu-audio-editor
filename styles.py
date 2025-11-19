DARK_THEME = """
QMainWindow { background-color: #2b2b2b; }
QWidget { color: #e0e0e0; font-family: 'Segoe UI', sans-serif; font-size: 13px; }

/* Ribbon */
QFrame#Ribbon { background-color: #3c3c3c; border-bottom: 1px solid #1a1a1a; }

/* Buttons */
QPushButton { background-color: #505050; border: 1px solid #202020; border-radius: 3px; padding: 5px; }
QPushButton:hover { background-color: #606060; }
QPushButton:pressed { background-color: #404040; }

/* Scroll Areas */
QScrollArea { border: none; background-color: #202020; }
QScrollBar:vertical { background: #2b2b2b; width: 12px; }
QScrollBar::handle:vertical { background: #505050; border-radius: 4px; }

/* Tracks */
QFrame#TrackHeader { background-color: #333333; border-bottom: 1px solid #1a1a1a; border-right: 1px solid #1a1a1a; }
QFrame#TrackLane { background-color: #202020; border-bottom: 1px solid #303030; }
"""