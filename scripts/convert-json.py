#!/usr/bin/env python3


import json
import pandas as pd
from pretty_cli import PrettyCli


def main() -> None:
    cli = PrettyCli()
    cli.main_title("Convert JSON")

    # ================================================================ #
    cli.section("Loading Data")

    with open("data/complete.json", encoding="utf-8") as file:
        js = json.load(file)

    cli.print("Read OK")
    # print(pd.Series(entry["level"] for entry in js).value_counts())
    # return

    # print(max(len(form["meanings"]) for entry in js for form in entry["forms"]))

    # ================================================================ #
    cli.section("Extracting Subset")

    df = pd.DataFrame()

    pinyin_counts = []

    for entry in js:
        levels = [l for l in entry["level"] if l.startswith("old-")]
        if len(levels) < 1:
            continue
        level = int(levels[0][4:])

        pinyin_counts.append(len(pd.Series([ form["transcriptions"]["pinyin"] for form in entry["forms"]]).unique()))

        for form in entry["forms"]:
            row = pd.DataFrame({
                "hanzi": entry["simplified"],
                "level": level,
                "frequency": int(entry["frequency"]),
                "pinyin": form["transcriptions"]["pinyin"],
                "meanings": form["meanings"],
            })

            df = pd.concat([ df, row ])

        # print(entry)
        # break

    df = df.sort_values(by=["level", "frequency", "pinyin"], ascending=True)

    cli.print(df)
    cli.small_divisor()
    cli.print(pd.Series(pinyin_counts).describe())

    # # ================================================================ #
    cli.section("Saving Data")
    df.to_csv("data/hsk.csv", index=False)
    cli.print("Write OK")


if __name__ == "__main__":
    main()
