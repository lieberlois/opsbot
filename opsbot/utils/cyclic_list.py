#coding=utf-8
from dataclasses import dataclass, field
from typing import List, Any


@dataclass
class CyclicList(object):
    elements: List[Any]
    dynamic: bool = False
    current_index: int = field(init=False, default=-1)

    def size(self):
        return len(self.elements)

    def add_element(self, value):
        already_exists = value in self.elements
        if not already_exists:
            self.elements.append(value)
        self.dynamic = True
        return not already_exists

    def remove_element(self, value):
        if value in self.elements:
            self.elements.remove(value)

    def _increment(self):
        idx = self.current_index + 1
        return idx % len(self.elements)

    def _decrement(self):
        idx = self.current_index - 1
        return idx % len(self.elements)

    def previous(self):
        self.current_index = self._decrement()
        return self.elements[self.current_index]

    def next(self):
        self.current_index = self._increment()
        return self.elements[self.current_index]

    def peek(self):
        return self.elements[self._increment()]
    
    def peek_n(self, n):
        idx = self.current_index + n
        idx = idx % len(self.elements)
        return self.elements[idx]

    def get(self):
        return self.elements[self.current_index]

    def goto(self, element):
        try:
            self.current_index = self.elements.index(element)
            return self.elements[self.current_index]
        except ValueError:
            return None

    def back(self):
        self.current_index = self._increment()
        return self.elements[self.current_index]

    def get_state(self):
        state = dict(index=self.current_index)
        if self.dynamic:
            state["elements"] = self.elements
        return state

    def load_state(self, state):
        if not state:
            return
        if "index" in state:
            self.current_index = state["index"]
        if "elements" in state:
            self.dynamic = True
            self.elements = state["elements"]
