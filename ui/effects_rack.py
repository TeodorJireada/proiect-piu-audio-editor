
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, QListWidget, QListWidgetItem, QLabel, QSizePolicy, QAbstractItemView
from PySide6.QtCore import Qt, Signal, QSize
from ui.widgets.effect_unit import EffectUnit

from core.effects.eq import EQ3Band
from core.effects.delay import SimpleDelay
from core.effects.distortion import Distortion
from core.commands import AddEffectCommand, RemoveEffectCommand, ReorderEffectCommand

class EffectsListWidget(QListWidget):
    """Custom ListWidget to handle drag and drop of effects"""
    reorder_requested = Signal(int, int) # old_index, new_index

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)
        # Style to make it look clean
        self.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                border: none;
                outline: none;
            }
            QListWidget::item {
                background-color: transparent;
                padding: 2px;
            }
            QListWidget::item:selected {
                background-color: transparent; 
                border: none;
            }
        """)

    def dropEvent(self, event):
        # Calculate indices
        source_item = self.currentItem()
        if not source_item:
            event.ignore()
            return
            
        old_index = self.row(source_item)
        
        # Calculate drop index
        # This is tricky in QListWidget. simpler to let super() handle it?
        # If we let super handle it, the UI updates but model is out of sync.
        # We want to intercept, calculate where it WOULD go, and emit signal.
        
        # Determine index from position
        pos = event.position().toPoint()
        target_item = self.itemAt(pos)
        
        if target_item:
            new_index = self.row(target_item)
            # Logic for above/below?
            # QListWidget usually drops *before* item if not careful.
            # Visual indicator handles this.
            
            # Use View's drop logic to get proposed action
            drop_indicator_pos = self.dropIndicatorPosition()
            if drop_indicator_pos == QAbstractItemView.BelowItem:
                 new_index += 1
            elif drop_indicator_pos == QAbstractItemView.OnViewport:
                 new_index = self.count() - 1
        else:
            new_index = self.count() - 1 # End of list
            
        # If dropping at same index or invalid
        if new_index == old_index:
            event.ignore()
            return

        # Adjust for removal
        # If we move item 0 to position 2 (insert after 1):
        # [0, 1, 2] -> 0 moves. new list: [1, 2] -> insert at 2.
        # If target index > source index, we must subtract 1 because source is removed first?
        # Logic: 
        # Source i=0. Target i=2 (Below item 1).
        # Pop 0. List is [1, 2]. Insert at 2 (end). Result [1, 2, 0]. Correct.
        # However, new_index from QListWidget accounts for current state.
        
        if new_index > old_index:
             new_index -= 1

        self.reorder_requested.emit(old_index, new_index)
        event.ignore() # Don't let QListWidget do it locally. Command triggers refresh.

class EffectsRack(QWidget):
    effects_changed = Signal() 

    def __init__(self, undo_stack, parent=None):
        super().__init__(parent)
        self.undo_stack = undo_stack
        self.current_track = None
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Header
        header = QHBoxLayout()
        self.lbl_title = QLabel("Effects Rack (No Track Selected)")
        self.lbl_title.setStyleSheet("font-weight: bold; color: #88ccff;")
        header.addWidget(self.lbl_title)
        
        self.combo_add = QComboBox()
        self.combo_add.addItem("Add Effect...", None)
        self.combo_add.addItem("EQ 3-Band", EQ3Band)
        self.combo_add.addItem("Delay", SimpleDelay)
        self.combo_add.addItem("Distortion", Distortion)
        self.combo_add.currentIndexChanged.connect(self.on_add_effect)
        
        header.addWidget(self.combo_add)
        self.main_layout.addLayout(header)
        
        # Scroll Area REPLACED by ListWidget
        self.list_widget = EffectsListWidget()
        self.list_widget.reorder_requested.connect(self.on_reorder_effect)
        
        self.main_layout.addWidget(self.list_widget)
        
    def set_track(self, track_data):
        self.current_track = track_data
        if not track_data:
            self.lbl_title.setText("Effects Rack (No Track Selected)")
            self.combo_add.setEnabled(False)
            self.clear_rack()
        else:
            self.lbl_title.setText(f"Effects: {track_data.name}")
            self.combo_add.setEnabled(True)
            self.refresh_rack()
            
    def clear_rack(self):
        self.list_widget.clear()
                
    def refresh_rack(self):
        self.clear_rack()
        if not self.current_track: return
        
        self.effects_changed.emit() # Notify listeners (TrackManager)
        
        for effect in self.current_track.effects:
            unit = EffectUnit(effect, self.undo_stack)
            
            # wrapper to add delete button and drag handle
            wrapper = QWidget()
            h = QHBoxLayout(wrapper)
            h.setContentsMargins(2, 2, 2, 2)
            
            # Drag Handle
            lbl_grip = QLabel("::")
            lbl_grip.setFixedWidth(15)
            lbl_grip.setStyleSheet("color: #666; font-weight: bold; font-size: 14px;")
            lbl_grip.setAlignment(Qt.AlignCenter)
            h.addWidget(lbl_grip)
            
            # Unit
            h.addWidget(unit)
            
            # Delete Button
            btn_del = QPushButton("X")
            btn_del.setFixedSize(20, 50) # Tall thin button
            btn_del.setStyleSheet("background-color: #552222;")
            btn_del.clicked.connect(lambda checked=False, e=effect: self.remove_effect(e))
            
            h.addWidget(btn_del)
            
            # Create List Item
            item = QListWidgetItem(self.list_widget)
            item.setSizeHint(wrapper.sizeHint())
            
            self.list_widget.setItemWidget(item, wrapper)
            
    def on_add_effect(self, index):
        if index <= 0: return
        
        effect_class = self.combo_add.currentData()
        if effect_class and self.current_track:
            effect_instance = effect_class()
            cmd = AddEffectCommand(self, self.current_track, effect_instance)
            self.undo_stack.push(cmd)
            
        self.combo_add.setCurrentIndex(0) # Reset
        
    def remove_effect(self, effect):
        if self.current_track:
            cmd = RemoveEffectCommand(self, self.current_track, effect)
            self.undo_stack.push(cmd)

    def on_reorder_effect(self, old_index, new_index):
        if self.current_track:
            cmd = ReorderEffectCommand(self, self.current_track, old_index, new_index)
            self.undo_stack.push(cmd)
