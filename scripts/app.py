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
    index: int
    """Position of this entry in the `State.data` list."""


class State:
    data       : list[Entry]
    rng        : random.Random
    level_tops : list[int]
    weights    : float

    min_level : int
    max_level : int

    entry_history : list[Entry]
    """Timeline of entries that have been picked so far."""
    current_entry : int
    """Index into the `entry_history` array indicating where we are in the timeline."""
    prob_modifier : int
    """Indicates wether the `current_entry`'s probability of being picked should be increased (+1), decreased (-1), or kept the same (0)."""

    show_pinyin : bool

    MAX_HISTORY : int = 128

    WEIGHT_MULTIPLIER : float = 2.0
    MIN_WEIGHT        : float = 1.0
    STARTING_WEIGHT   : float = MIN_WEIGHT * (WEIGHT_MULTIPLIER ** 6)
    MAX_WEIGHT        : float = STARTING_WEIGHT * (WEIGHT_MULTIPLIER ** 6)

    def __init__(self):
        csv_data = pd.read_csv("data/hsk-manual.csv")
        self.data = [ self._entry_from_csv(csv_data, i) for i in csv_data.index ]
        self.level_tops = [ int(csv_data.index[csv_data["level"] <= i+1].max()) for i in range(6) ]
        self.weights = [ self.STARTING_WEIGHT for _ in self.data ]
        self.rng = random.Random()

        self.min_level = 1
        self.max_level = 3

        self.entry_history = [ self.get_random_entry() ]
        self.current_entry = 0
        self.prob_modifier = 0

        self.show_pinyin = False

    def _entry_from_csv(self, csv_data: pd.DataFrame, index: int) -> Entry:
        assert index in csv_data.index, f"{index=} not contained in {csv_data.index=}"
        row = csv_data.loc[index]

        level = int(row["level"])
        characters = [ char for char in row["hanzi"] ]
        pinyin = row["pinyin"].split()
        meanings = [ entry.strip() for entry in row["meanings"].split(";") ]

        assert 1 <= level <= 6, f"[{index=}] Expected 1 <= level <= 6; found {level=}"
        assert len(characters) > 0, f"[{index=}] Expected at leas one character, found none!"
        assert len(characters) == len(pinyin), f"[{index=}] Expected characters and pinyin to have the same length; found {len(characters)=}; {len(pinyin)}. {characters=}; {pinyin=}"
        assert len(meanings) > 0, f"[{index=}] Expected at leas one meaning, found none!"

        return Entry(level, characters, pinyin, meanings, index)

    def set_min_level(self, level: int) -> None:
        assert 1 <= level <= 6, f"Expected 1 <= level <= 6; found {level=}"
        assert level <= self.max_level, f"Expected level <= self.max_level. Found {level=}; {self.max_level=}"
        self.min_level = level

    def set_max_level(self, level: int) -> None:
        assert 1 <= level <= 6, f"Expected 1 <= level <= 6; found {level=}"
        assert self.min_level <= level, f"Expected self.min_level <= level. Found {level=}; {self.min_level=}"
        self.max_level = level

    def get_random_entry(self) -> Entry:
        # We have to shift the levels from 1-indexed to 0-indexed when looking up values in level_tops.
        # Since we store the top inclusive, the bottom is the previous top + 1.
        bottom = 0 if self.min_level < 2 else self.level_tops[self.min_level - 2] + 1
        top = self.level_tops[self.max_level-1]

        entry = self.rng.choices(population=self.data[bottom:top+1], weights=self.weights[bottom:top+1])[0]
        return entry

    def change_current_entry(self, new_idx: int) -> Entry:
        """
        Changes which entry is the current entry, and does any necessary updates and cleanup.
        Returns the new current entry.

        new_idx : int
            Index into the `entry_history` list.
        """
        assert 0 <= self.current_entry < len(self.entry_history), f"Expected 0 <= self.current_entry <= {len(self.entry_history)}, but found {self.current_entry=}"
        assert 0 <= new_idx < len(self.entry_history), f"Expected 0 <= new_idx <= {len(self.entry_history)}, but found {new_idx=}"

        old_entry = self.entry_history[self.current_entry]
        new_entry = self.entry_history[new_idx]

        if new_idx == self.current_entry:
            # Early exit, nothing to change.
            return old_entry

        if (self.prob_modifier > 0) and (self.weights[old_entry.index] < self.MAX_WEIGHT):
            self.weights[old_entry.index] *= 2.0
        elif (self.prob_modifier < 0) and (self.weights[old_entry.index] > self.MIN_WEIGHT):
            self.weights[old_entry.index] /= 2.0

        self.current_entry = new_idx
        self.prob_modifier = 0

        return new_entry

    def get_current_entry(self) -> Entry:
        """Returns the current entry."""
        assert 0 <= self.current_entry < len(self.entry_history), f"Expected 0 <= self.current_entry <= {len(self.entry_history)}, but found {self.current_entry=}"
        return self.entry_history[self.current_entry]

    def move_to_previous_entry(self) -> Entry:
        """If there are earlier entries in the timeline, moves back to the immediately previous one and does any necessary updates and cleanup."""
        return self.change_current_entry(new_idx=max(0, self.current_entry - 1))

    def move_to_next_entry(self) -> Entry:
        """
        If there are later entries in the timeline, moves to the immediately next entry.
        Otherwise, creates a new random entry at the front.
        In any case, does any necessary updates and cleanup.
        """

        if self.current_entry == len(self.entry_history) - 1:
            self.entry_history.append(self.get_random_entry())

            if len(self.entry_history) > self.MAX_HISTORY:
                self.entry_history.pop(0)

            new_idx = len(self.entry_history) - 1
        else:
            new_idx = self.current_entry + 1

        return self.change_current_entry(new_idx)

    def move_to_first_entry(self) -> Entry:
        """
        Moves to the very first entry in the entry history.
        Does any necessary updates and cleanup.
        """
        return self.change_current_entry(new_idx=0)

    def move_to_new_entry(self) -> Entry:
        """
        Moves to the front of the entry history and adds a new random entry.
        Does any necessary updates and cleanup.
        """
        if self.current_entry < len(self.entry_history) - 1:
            self.change_current_entry(len(self.entry_history) - 1)

        return self.move_to_next_entry()


class LevelSelector(QtWidgets.QWidget):
    state     : State

    min_group : QtWidgets.QButtonGroup
    max_group : QtWidgets.QButtonGroup
    layout    : QtWidgets.QLayout

    def __init__(self, state: State):
        super().__init__()
        self.state = state
        self.init_ui()

    def init_ui(self) -> None:
        self.layout = QtWidgets.QVBoxLayout()

        self.min_group = self._make_button_row(
            label="Min level:",
            initial_value=self.state.min_level,
            on_click=self._set_min_level,
        )

        self.max_group = self._make_button_row(
            label="Max level:",
            initial_value=self.state.max_level,
            on_click=self._set_max_level,
        )

        self.setLayout(self.layout)
        self.update_ui()

    def _make_button_row(self, label: str, initial_value: int, on_click: Callable[[int], None]) -> QtWidgets.QButtonGroup:
        row_layout = QtWidgets.QHBoxLayout()

        row_label = QtWidgets.QLabel(label)
        row_layout.addWidget(row_label)

        button_group = QtWidgets.QButtonGroup(exclusive=True)
        button_group.idClicked.connect(on_click)

        for i in range(1, 7):
            button = QtWidgets.QPushButton(text=str(i), checkable=True, checked=(i == initial_value))
            button_group.addButton(button, id=i)
            row_layout.addWidget(button)

        self.layout.addLayout(row_layout)
        return button_group

    def _set_min_level(self, level: int) -> None:
        self.state.set_min_level(level)
        self.update_ui()

    def _set_max_level(self, level: int) -> None:
        self.state.set_max_level(level)
        self.update_ui()

    def update_ui(self) -> None:
        min_buttons = self.min_group.buttons()
        max_buttons = self.max_group.buttons()

        for i in range(6):
            min_buttons[i].setEnabled(i <= self.state.max_level - 1)
            max_buttons[i].setEnabled(i >= self.state.min_level - 1)

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

    button_prev  : QtWidgets.QPushButton
    button_show  : QtWidgets.QPushButton
    button_next  : QtWidgets.QPushButton
    button_plus  : QtWidgets.QPushButton
    button_minus : QtWidgets.QPushButton

    on_prev              : Callable[[], None]
    on_next              : Callable[[], None]
    on_toggle_visibility : Callable[[], None]

    icon_show  : QtGui.QIcon
    icon_hide  : QtGui.QIcon
    icon_prev  : QtGui.QIcon
    icon_next  : QtGui.QIcon
    icon_plus  : QtGui.QIcon
    icon_minus : QtGui.QIcon

    def __init__(self, state: State, on_prev: Callable[[], None], on_next: Callable[[], None], on_toggle_visibility: Callable[[], None]):
        super().__init__()

        self.state = state
        self.on_prev = on_prev
        self.on_next = on_next
        self.on_toggle_visibility = on_toggle_visibility

        self.init_ui()

    def init_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout()

        self.icon_show = QtGui.QIcon("data/eye.png")
        self.icon_hide = QtGui.QIcon("data/eye-slash.png")
        self.icon_next = QtGui.QIcon("data/square-caret-right.png")
        self.icon_prev = QtGui.QIcon("data/square-caret-left.png")
        self.icon_plus = QtGui.QIcon("data/square-plus.png")
        self.icon_minus = QtGui.QIcon("data/square-minus.png")

        # ---------------------------------------------------------------- #

        first_row = QtWidgets.QHBoxLayout()

        self.button_prev = QtWidgets.QPushButton(text="Prev")
        self.button_prev.setIcon(self.icon_prev)
        self.button_prev.setToolTip("Backspace")
        self.button_prev.clicked.connect(self.on_prev)
        first_row.addWidget(self.button_prev)

        self.button_show = QtWidgets.QPushButton(text="Show")
        self.button_show.setIcon(self.icon_show)
        self.button_show.setToolTip("Space")
        self.button_show.clicked.connect(self.on_toggle_visibility)
        first_row.addWidget(self.button_show)

        self.button_next = QtWidgets.QPushButton(text="Next")
        self.button_next.setIcon(self.icon_next)
        self.button_next.setToolTip("Enter")
        self.button_next.clicked.connect(self.on_next)
        first_row.addWidget(self.button_next)

        layout.addLayout(first_row)

        # ---------------------------------------------------------------- #

        second_row = QtWidgets.QHBoxLayout()

        self.button_plus = QtWidgets.QPushButton(text="Show More", checkable=True)
        self.button_plus.setIcon(self.icon_plus)
        self.button_plus.setToolTip("+")
        self.button_plus.clicked.connect(self.on_plus)
        second_row.addWidget(self.button_plus)

        self.button_minus = QtWidgets.QPushButton(text="Show Less", checkable=True)
        self.button_minus.setIcon(self.icon_minus)
        self.button_minus.setToolTip("-")
        self.button_minus.clicked.connect(self.on_minus)
        second_row.addWidget(self.button_minus)

        layout.addLayout(second_row)

        # ---------------------------------------------------------------- #

        self.setLayout(layout)
        self.update_ui()

    def update_ui(self) -> None:
        if self.state.show_pinyin:
            self.button_show.setText("Hide")
            self.button_show.setIcon(self.icon_hide)
        else:
            self.button_show.setText("Show")
            self.button_show.setIcon(self.icon_show)

        self.button_plus.setChecked(self.state.prob_modifier > 0)
        self.button_minus.setChecked(self.state.prob_modifier < 0)

    def on_plus(self) -> None:
        self.state.prob_modifier = 0 if (self.state.prob_modifier > 0) else +1
        self.update_ui()

    def on_minus(self) -> None:
        self.state.prob_modifier = 0 if (self.state.prob_modifier < 0) else -1
        self.update_ui()


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
        self.level_selector.update_ui()
        self.text_display.populate()
        self.meaning_display.populate()
        self.control_buttons.update_ui()

    def toggle_pinyin(self) -> None:
        self.state.show_pinyin = not self.state.show_pinyin
        self.refresh()

    def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if event.type() == QtCore.QEvent.KeyPress:
            if event.key() == Qt.Key_Backspace:
                self.step_back()
                return True

            if event.key() == Qt.Key_Return:
                self.step_forward()
                return True

            if event.key() == Qt.Key_Minus:
                self.control_buttons.on_minus()
                return True

            if event.key() == Qt.Key_Equal: # It's the key that has the plus sign in US layout.
                self.control_buttons.on_plus()
                return True

            if event.key() == Qt.Key_Space:
                self.toggle_pinyin()
                return True

            if event.key() == Qt.Key_Escape:
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
