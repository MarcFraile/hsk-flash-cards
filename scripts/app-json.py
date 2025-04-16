#!/usr/bin/env python3


import sys, random
from dataclasses import dataclass

import pandas as pd
from PySide6 import QtCore, QtWidgets, QtGui


def clear_layout(layout: QtWidgets.QLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()


@dataclass
class Entry:
    level      : int
    characters : list[str]
    pinyin     : list[str]
    meanings   : list[str]


class State:
    data       : pd.DataFrame
    rng        : random.Random
    level_tops : list[int]

    current_level : int
    current_entry : Entry

    def __init__(self):
        self.data = pd.read_csv("data/hsk-manual.csv")
        self.rng = random.Random()
        self.level_tops = [ int(self.data.index[self.data["level"] <= i+1].max()) for i in range(6) ]

        self.current_level = 1
        self.current_entry = self.get_random_entry()

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
        print(f"{self.current_level=}")

    def get_random_entry(self) -> Entry:
        top = self.level_tops[self.current_level-1]
        idx = self.rng.randint(0, top)
        entry = self.get_entry(idx)
        return entry

    def randomize_entry(self) -> Entry:
        self.current_entry = self.get_random_entry()
        print(f"{self.current_entry=}")


class LevelSelector(QtWidgets.QWidget):
    state: State
    level_group: QtWidgets.QButtonGroup

    def __init__(self, state: State):
        super().__init__()
        self.state = state
        self.init_ui()

    def init_ui(self) -> None:
        level_layout = QtWidgets.QHBoxLayout()
        self.level_group = QtWidgets.QButtonGroup(exclusive=True)

        for i in range(1, 7):
            button = QtWidgets.QPushButton(text=str(i), checkable=True, checked=(i == self.state.current_level))
            self.level_group.addButton(button, id=i)
            level_layout.addWidget(button)

        self.level_group.idClicked.connect(self.state.set_current_level)
        self.setLayout(level_layout)

class TextDisplay(QtWidgets.QWidget):
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
        self.layout.setAlignment(QtCore.Qt.AlignCenter)

        self.setLayout(self.layout)
        self.populate()

    def populate(self) -> None:
        clear_layout(self.layout)

        entry = self.state.current_entry

        for i, (character, pinyin) in enumerate(zip(entry.characters, entry.pinyin)):
            pinyin_label = QtWidgets.QLabel(pinyin)
            pinyin_label.setFont(self.latin_font)
            pinyin_label.setAlignment(QtCore.Qt.AlignCenter)

            character_label = QtWidgets.QLabel(character)
            character_label.setFont(self.character_font)
            character_label.setAlignment(QtCore.Qt.AlignCenter)

            self.layout.addWidget(pinyin_label   , 0, i)
            self.layout.addWidget(character_label, 1, i)


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
        self.layout.setAlignment(QtCore.Qt.AlignCenter)
        self.setLayout(self.layout)
        self.populate()

    def populate(self) -> None:
        clear_layout(self.layout)

        entry = self.state.current_entry

        for meaning in entry.meanings:
            meaning_label = QtWidgets.QLabel(text=meaning)
            meaning_label.setFont(self.latin_font)
            meaning_label.setAlignment(QtCore.Qt.AlignCenter)
            self.layout.addWidget(meaning_label)


def main() -> None:
    state = State()

    app = QtWidgets.QApplication(sys.argv)
    window = QtWidgets.QWidget(windowTitle="HSK Flashcards", windowIcon=QtGui.QIcon("data/字.png"))
    main_layout = QtWidgets.QVBoxLayout()

    latin_font = QtGui.QFont("Arial", pointSize=16)
    character_font = QtGui.QFont("KaiTi", pointSize=80)

    level_selector = LevelSelector(state)
    main_layout.addWidget(level_selector)

    text_display = TextDisplay(state, latin_font, character_font)
    main_layout.addWidget(text_display, alignment=QtCore.Qt.AlignCenter)

    meaning_display = MeaningDisplay(state, latin_font)
    main_layout.addWidget(meaning_display)

    def randomize():
        state.randomize_entry()
        text_display.populate()
        meaning_display.populate()

    next_button = QtWidgets.QPushButton(text="Next ⏭")
    next_button.clicked.connect(randomize)
    main_layout.addWidget(next_button)

    window.setLayout(main_layout)
    window.resize(16 * 16 * 2, 16 * 9 * 2)
    window.show()

    randomize()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
