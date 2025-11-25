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
QFrame#TrackLane { background-color: transparent; border-bottom: 1px solid #303030; }
QWidget#TrackContainer { background-color: #2b2b2b; }

/* Splitter */
QSplitter::handle { background-color: #111; }

/* Top Left Corner */
QFrame#TopLeftCorner { background-color: #252525; border-bottom: 1px solid #1a1a1a; border-right: 1px solid #1a1a1a; }

/* Add Track Button */
QPushButton#AddTrackButton {
    background-color: #333;
    color: #aaa;
    border: 1px dashed #555;
    font-size: 24px;
    font-weight: bold;
}
QPushButton#AddTrackButton:hover {
    background-color: #444;
    color: white;
    border: 1px dashed #777;
}

/* Track Header Components */
QLabel#TrackNameLabel { font-weight: bold; font-size: 12px; color: #e0e0e0; }

QPushButton#TrackDeleteButton { background-color: #444; color: #aaa; border: none; }
QPushButton#TrackDeleteButton:hover { background-color: #ff3333; color: white; }

/* Mute/Solo State Styles (applied via dynamic properties or separate classes if possible, 
   but for now we might keep state logic local or use property selectors) */
QPushButton[muted="true"] { background-color: #ff4444; color: white; border: 1px solid #ff0000; }
QPushButton[muted="false"] { background-color: #442222; color: #ffaaaa; border: 1px solid #331111; }

QPushButton[soloed="true"] { background-color: #44ff44; color: black; border: 1px solid #00ff00; }
QPushButton[soloed="false"] { background-color: #224422; color: #aaffaa; border: 1px solid #113311; }
"""