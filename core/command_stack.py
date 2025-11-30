from PySide6.QtCore import QObject, Signal

class Command:
    def execute(self):
        raise NotImplementedError

    def undo(self):
        raise NotImplementedError

class UndoStack(QObject):
    stack_changed = Signal()

    def __init__(self, limit=50):
        super().__init__()
        self._undo_stack = []
        self._redo_stack = []
        self.limit = limit

    def push(self, command):
        self._redo_stack.clear()
        command.execute()
        self._undo_stack.append(command)
        if len(self._undo_stack) > self.limit:
            self._undo_stack.pop(0)
        self.stack_changed.emit()

    def undo(self):
        if not self._undo_stack:
            return
        command = self._undo_stack.pop()
        command.undo()
        self._redo_stack.append(command)
        self.stack_changed.emit()

    def redo(self):
        if not self._redo_stack:
            return
        command = self._redo_stack.pop()
        command.execute()
        self._undo_stack.append(command)
        self.stack_changed.emit()

    def can_undo(self):
        return len(self._undo_stack) > 0

    def can_redo(self):
        return len(self._redo_stack) > 0
