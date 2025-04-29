#!/usr/bin/env python3


import sys, random
from dataclasses import dataclass
from typing import Callable

import pandas as pd
from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import Qt


def clear_layout(layout: QtWidgets.QLayout) -> None:
    """Remove all children from `layout`."""
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()


@dataclass
class Entry:
    """Single entry in the word database."""
    level : int
    """Which HSK2.0 level does this word or expression belong to?"""
    characters : list[str]
    """The simplified Chinese characters in this word or expression, as a list of individual characters."""
    pinyin : list[str]
    """The pinyin spellings of each character in this word or expression."""
    meanings : list[str]
    """Different ways to translate this word or expression into English."""


class State:
    data       : pd.DataFrame
    rng        : random.Random
    level_tops : list[int]

    current_level : int # TODO: Consider doing min-max range.

    entry_history : list[Entry]
    current_entry : int

    show_pinyin : bool

    MAX_HISTORY : int = 128

    def __init__(self):
        self.data = pd.read_csv("data/hsk-manual.csv")
        self.rng = random.Random()
        self.level_tops = [ int(self.data.index[self.data["level"] <= i+1].max()) for i in range(6) ]

        self.current_level = 1
        self.entry_history = [ self.get_random_entry() ]
        self.current_entry = 0
        self.show_pinyin = False

    def get_entry(self, idx: int) -> Entry:
        assert idx in self.data.index, f"Expected a valid index, but {idx=} not contained in {self.data.index=}"
        row = self.data.loc[idx]

        level = int(row["level"])
        characters = [ char for char in row["hanzi"] ]
        pinyin = row["pinyin"].split()
        meanings = [ entry.strip() for entry in row["meanings"].split(";") ]

        assert 1 <= level <= 6, f"[{idx=}] Expected 1 <= level <= 6; found {level=}"
        assert len(characters) > 0, f"[{idx=}] Expected at leas one character, found none!"
        assert len(characters) == len(pinyin), f"[{idx=}] Expected characters and pinyin to have the same length; found {len(characters)=}; {len(pinyin)}. {characters=}; {pinyin=}"
        assert len(meanings) > 0, f"[{idx=}] Expected at leas one meaning, found none!"

        return Entry(level, characters, pinyin, meanings)

    def set_current_level(self, level: int) -> None:
        assert 1 <= level <= 6, f"Expected 1 <= level <= 6; found {level=}"
        self.current_level = level

    def get_random_entry(self) -> Entry:
        top = self.level_tops[self.current_level-1]
        idx = self.rng.randint(0, top)
        entry = self.get_entry(idx)
        return entry

    def get_current_entry(self) -> Entry:
        assert 0 <= self.current_entry < len(self.entry_history)
        return self.entry_history[self.current_entry]

    def move_to_previous_entry(self) -> Entry:
        if self.current_entry > 0:
            self.current_entry -= 1
        return self.get_current_entry()

    def move_to_next_entry(self) -> Entry:
        if self.current_entry < len(self.entry_history) - 1:
            self.current_entry += 1
        else:
            self.entry_history.append(self.get_random_entry())
            if len(self.entry_history) > self.MAX_HISTORY:
                self.entry_history.pop(0)
            self.current_entry = len(self.entry_history) - 1
        return self.get_current_entry()


class LevelSelector(QtWidgets.QWidget):
    state: State
    level_group: QtWidgets.QButtonGroup

    def __init__(self, state: State):
        super().__init__()
        self.state = state
        self.init_ui()

    def init_ui(self) -> None:
        level_layout = QtWidgets.QHBoxLayout()

        level_label = QtWidgets.QLabel("Max level:")
        level_layout.addWidget(level_label)

        self.level_group = QtWidgets.QButtonGroup(exclusive=True)

        for i in range(1, 7):
            button = QtWidgets.QPushButton(text=str(i), checkable=True, checked=(i == self.state.current_level))
            self.level_group.addButton(button, id=i)
            level_layout.addWidget(button)

        self.level_group.idClicked.connect(self.state.set_current_level)
        self.setLayout(level_layout)

class TextDisplayInner(QtWidgets.QWidget):
    state          : State
    latin_font     : QtGui.QFont
    character_font : QtGui.QFont
    layout         : QtWidgets.QLayout

    def __init__(self, state: State, latin_font: QtGui.QFont, character_font: QtGui.QFont):
        super().__init__()

        self.state = state
        self.latin_font = latin_font
        self.character_font = character_font

        self.init_ui()

    def init_ui(self) -> None:
        self.layout = QtWidgets.QGridLayout()
        self.layout.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)
        self.layout.setAlignment(Qt.AlignCenter)

        self.setLayout(self.layout)
        self.populate()

    def populate(self) -> None:
        clear_layout(self.layout)

        entry = self.state.get_current_entry()

        for i, (character, pinyin) in enumerate(zip(entry.characters, entry.pinyin)):
            if self.state.show_pinyin:
                pinyin_label = QtWidgets.QLabel(pinyin)
                pinyin_label.setFont(self.latin_font)
                pinyin_label.setAlignment(Qt.AlignCenter)
                self.layout.addWidget(pinyin_label   , 0, i)

            character_label = QtWidgets.QLabel(character)
            character_label.setFont(self.character_font)
            character_label.setAlignment(Qt.AlignCenter)
            self.layout.addWidget(character_label, 1, i)


class TextDisplay(QtWidgets.QWidget):
    state         : State
    inner_display : TextDisplayInner
    hsk_display   : QtWidgets.QLabel

    def __init__(self, state: State, latin_font: QtGui.QFont, character_font: QtGui.QFont):
        super().__init__()

        self.state = state
        self.inner_display = TextDisplayInner(state, latin_font, character_font)

        self.init_ui()

    def init_ui(self) -> None:
        layout = QtWidgets.QGridLayout()
        self.setLayout(layout)

        self.hsk_display = QtWidgets.QLabel()
        self.hsk_display.setStyleSheet("color: green")
        self.hsk_display.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)

        layout.addWidget(self.inner_display, 0, 0)
        layout.addWidget(self.hsk_display, 0, 0)

        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        self.populate()

    def populate(self) -> None:
        self.inner_display.populate()
        entry = self.state.get_current_entry()
        self.hsk_display.setText(f"HSK{entry.level}")


class MeaningDisplay(QtWidgets.QWidget):
    state      : State
    latin_font : QtGui.QFont
    layout     : QtWidgets.QLayout

    def __init__(self, state: State, latin_font: QtGui.QFont):
        super().__init__()

        self.state = state
        self.latin_font = latin_font

        self.init_ui()

    def init_ui(self) -> None:
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.setAlignment(Qt.AlignCenter)
        self.setLayout(self.layout)
        self.populate()

    def populate(self) -> None:
        clear_layout(self.layout)

        if not self.state.show_pinyin:
            return

        entry = self.state.get_current_entry()

        for meaning in entry.meanings:
            meaning_label = QtWidgets.QLabel(text=meaning)
            meaning_label.setFont(self.latin_font)
            meaning_label.setAlignment(Qt.AlignCenter)
            self.layout.addWidget(meaning_label)


class ControlButtons(QtWidgets.QWidget):
    state : State

    prev_button : QtWidgets.QPushButton
    show_button : QtWidgets.QPushButton
    next_button : QtWidgets.QPushButton

    on_prev              : Callable[[], None]
    on_next              : Callable[[], None]
    on_toggle_visibility : Callable[[], None]

    icon_show : QtGui.QIcon
    icon_hide : QtGui.QIcon
    icon_next : QtGui.QIcon
    icon_prev : QtGui.QIcon

    def __init__(self, state: State, on_prev: Callable[[], None], on_next: Callable[[], None], on_toggle_visibility: Callable[[], None]):
        super().__init__()

        self.state = state
        self.on_prev = on_prev
        self.on_next = on_next
        self.on_toggle_visibility = on_toggle_visibility

        self.init_ui()

    def init_ui(self) -> None:
        layout = QtWidgets.QHBoxLayout()
        layout.setAlignment(Qt.AlignCenter)

        self.icon_show = QtGui.QIcon("data/eye.png")
        self.icon_hide = QtGui.QIcon("data/eye-slash.png")
        self.icon_next = QtGui.QIcon("data/square-caret-right.png")
        self.icon_prev = QtGui.QIcon("data/square-caret-left.png")

        self.prev_button = QtWidgets.QPushButton(text="Prev")
        self.prev_button.setIcon(self.icon_prev)
        self.prev_button.setToolTip("Backspace")
        self.prev_button.clicked.connect(self.on_prev)
        layout.addWidget(self.prev_button)

        self.show_button = QtWidgets.QPushButton(text="Show")
        self.show_button.setIcon(self.icon_show)
        self.show_button.setToolTip("Space")
        self.show_button.clicked.connect(self.on_toggle_visibility)
        layout.addWidget(self.show_button)

        self.next_button = QtWidgets.QPushButton(text="Next")
        self.next_button.setIcon(self.icon_next)
        self.next_button.setToolTip("Enter")
        self.next_button.clicked.connect(self.on_next)
        layout.addWidget(self.next_button)

        self.setLayout(layout)
        self.update_ui()

    def update_ui(self) -> None:
        if self.state.show_pinyin:
            self.show_button.setText("Hide")
            self.show_button.setIcon(self.icon_hide)
        else:
            self.show_button.setText("Show")
            self.show_button.setIcon(self.icon_show)


class MainWindow(QtWidgets.QWidget):
    app            : QtWidgets.QApplication

    state          : State
    latin_font     : QtGui.QFont
    character_font : QtGui.QFont

    level_selector  : LevelSelector
    text_display    : TextDisplay
    meaning_display : MeaningDisplay
    control_buttons : ControlButtons

    def __init__(self, app: QtWidgets.QApplication):
        super().__init__(windowTitle="HSK Flashcards", windowIcon=QtGui.QIcon("data/字.png"))

        self.app = app

        self.state = State()
        self.latin_font = QtGui.QFont("Arial", pointSize=16)
        self.character_font = QtGui.QFont("KaiTi", pointSize=80)

        self.init_ui()

    def init_ui(self) -> None:
        main_layout = QtWidgets.QVBoxLayout()

        self.level_selector = LevelSelector(self.state)
        main_layout.addWidget(self.level_selector)

        self.text_display = TextDisplay(self.state, self.latin_font, self.character_font)
        main_layout.addWidget(self.text_display)

        self.meaning_display = MeaningDisplay(self.state, self.latin_font)
        main_layout.addWidget(self.meaning_display)

        self.control_buttons = ControlButtons(state=self.state, on_prev=self.step_back, on_next=self.step_forward, on_toggle_visibility=self.toggle_pinyin)
        main_layout.addWidget(self.control_buttons)

        self.setLayout(main_layout)

    def step_back(self) -> None:
        self.state.show_pinyin = False
        self.state.move_to_previous_entry()
        self.refresh()

    def step_forward(self) -> None:
        self.state.show_pinyin = False
        self.state.move_to_next_entry()
        self.refresh()

    def refresh(self) -> None:
        self.text_display.populate()
        self.meaning_display.populate()
        self.control_buttons.update_ui()

    def toggle_pinyin(self) -> None:
        self.state.show_pinyin = not self.state.show_pinyin
        self.refresh()

    def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if event.type() == QtCore.QEvent.KeyPress and event.key() == Qt.Key_Backspace:
            self.step_back()
            return True

        if event.type() == QtCore.QEvent.KeyPress and event.key() == Qt.Key_Return:
            self.step_forward()
            return True

        if event.type() == QtCore.QEvent.KeyPress and event.key() == Qt.Key_Space:
            self.toggle_pinyin()
            return True

        if event.type() == QtCore.QEvent.KeyPress and event.key() == Qt.Key_Escape:
            self.app.quit()
            return True

        return super().eventFilter(obj, event)


def main() -> None:
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow(app)
    app.installEventFilter(window)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
