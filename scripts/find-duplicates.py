#!/usr/bin/env python3


import pandas as pd
from pretty_cli import PrettyCli


def main() -> None:
    cli = PrettyCli()
    cli.main_title("Find Duplicates")

    # ================================================================ #
    cli.chapter("Loading Data")
    data = pd.read_csv("data/hsk-manual.csv")
    cli.print("OK")

    # ================================================================ #
    cli.chapter("Stats")

    # -------------------------------- #
    cli.section("Total Entries per Level")
    cli.print(data.groupby("level")["hanzi"].count())

    # -------------------------------- #
    cli.section("Entries with Hanzi and Pinyin Length Mismatch")

    hanzi_count = data["hanzi"].str.len()
    pinyin_count = data["pinyin"].str.split().apply(len)

    hanzi_mismatch = data[hanzi_count != pinyin_count]
    hanzi_mismatch.index.name = "row"
    hanzi_mismatch.index += 2

    cli.print(hanzi_mismatch)
    hanzi_mismatch.to_csv("data/hsk-manual-hanzi-pinyin-mismatch.csv")

    # -------------------------------- #
    cli.section("Unique Entries per Level")
    cli.print(data.groupby("level")["hanzi"].nunique())

    # -------------------------------- #
    cli.section("Repeated Entries")

    counts = data.groupby("level")["hanzi"].value_counts()
    counts = counts[counts > 1]

    cli.print(counts)
    counts.to_csv("data/hsk-manual-repetitions.csv")

    # -------------------------------- #
    cli.section("Repeated Entry Counts")
    cli.print(counts.index.get_level_values("level").value_counts().sort_index())


if __name__ == "__main__":
    main()
