#!/usr/bin/env python3


import sys, random
from dataclasses import dataclass

import pandas as pd
from PySide6 import QtCore, QtWidgets, QtGui


@dataclass
class Entry:
    character: str
    pinyin: str
    translation: str


@dataclass
class State:
    level: int
    current_entry: Entry


def main() -> None:
    data = pd.read_csv("data/hsk2.csv")
    rng = random.Random()

    def get_entry(idx):
        row = data.loc[idx]
        return Entry(character=row["character"], pinyin=row["pinyin"], translation=row["translation"])

    first_entry = data[data["character"] == "字"]
    first_entry = get_entry(first_entry.index.item())
    state = State(level=1, current_entry=first_entry)

    level_tops = { level: int(data.index[data["level"] <= level].max()) for level in range(1, 7) }
    print(level_tops)

    def get_random_entry():
        top = level_tops[state.level]
        idx = rng.randint(0, top)
        state.current_entry = get_entry(idx)
        update_view()

    app = QtWidgets.QApplication(sys.argv)
    window = QtWidgets.QWidget(windowTitle="HSK Flashcards", windowIcon=QtGui.QIcon("data/字.png"))
    main_layout = QtWidgets.QVBoxLayout()

    latin_font = QtGui.QFont("Arial", pointSize=16)
    character_font = QtGui.QFont("KaiTi", pointSize=80)

    level_layout = QtWidgets.QHBoxLayout()
    level_group = QtWidgets.QButtonGroup(exclusive=True)
    for i in range(1, 7):
        button = QtWidgets.QPushButton(text=str(i), checkable=True, checked=(i == state.level))
        level_group.addButton(button, id=i)
        level_layout.addWidget(button)
    def level_button_clicked(id):
        state.level = id
    level_group.idClicked.connect(level_button_clicked)
    main_layout.addLayout(level_layout)

    pinyin_box = QtWidgets.QLabel(state.current_entry.pinyin)
    pinyin_box.setFont(latin_font)
    pinyin_box.setAlignment(QtCore.Qt.AlignCenter)
    main_layout.addWidget(pinyin_box)

    character_box = QtWidgets.QLabel(state.current_entry.character)
    character_box.setFont(character_font)
    character_box.setAlignment(QtCore.Qt.AlignCenter)
    main_layout.addWidget(character_box)

    translation_box = QtWidgets.QLabel(state.current_entry.translation)
    translation_box.setFont(latin_font)
    translation_box.setAlignment(QtCore.Qt.AlignCenter)
    main_layout.addWidget(translation_box)

    next_button = QtWidgets.QPushButton(text="Next ⏭")
    next_button.clicked.connect(get_random_entry)
    main_layout.addWidget(next_button)

    window.setLayout(main_layout)
    window.resize(16 * 16 * 2, 16 * 9 * 2)
    window.show()

    def update_view():
        pinyin_box.setText(state.current_entry.pinyin)
        character_box.setText(state.current_entry.character)
        translation_box.setText(state.current_entry.translation)

    get_random_entry()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
