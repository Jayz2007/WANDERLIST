"""BACKEND / STUDENT MODIFICATION ZONE: backend/stack.py.

This RUNNABLE starter is deliberately NOT a stack yet. It keeps records in a
dictionary and takes the oldest record first (FIFO). The recovery tray calls
this class directly, so changing this file changes the real website.

YOUR CHALLENGE: replace the storage and operations with a real LIFO Stack.
Keep the public methods below so backend/app.py can continue calling them. You may
rename your class to Stack and add `HistoryBuffer = Stack` at the bottom.

Storage contract: to_list() returns values from oldest/bottom to newest/top.
The database saves that list and passes it to the constructor next request.
Do not change that contract when you change the removal rule.
"""


class HistoryBuffer:
    """Working FIFO baseline. Students must turn this into a LIFO structure."""

    def __init__(self, items=None):
        # TODO: replace this dictionary with your chosen stack representation.
        values = list(items) if items is not None else []
        self._records = {index: value for index, value in enumerate(values)}
        self._next_key = len(values)

    def push(self, item):
        """Record one removed item's ID."""
        # TODO: implement a stack push.
        self._records[self._next_key] = item
        self._next_key += 1

    def pop(self):
        """Take the next ID. Baseline currently takes the OLDEST one."""
        # TODO: implement LIFO removal and keep empty-history handling.
        if self.is_empty():
            raise IndexError("The recovery tray is empty.")
        oldest_key = min(self._records)
        return self._records.pop(oldest_key)

    def peek(self):
        """Read the next ID without removing it."""
        # TODO: make this agree with the top of your stack.
        if self.is_empty():
            raise IndexError("The recovery tray is empty.")
        oldest_key = min(self._records)
        return self._records[oldest_key]

    def is_empty(self):
        """True when there are no recovery records."""
        return len(self._records) == 0

    def size(self):
        """Number of recovery records."""
        return len(self._records)

    def to_list(self):
        """Return a NEW list in insertion order, ready to save in SQLite."""
        return [self._records[key] for key in sorted(self._records)]
