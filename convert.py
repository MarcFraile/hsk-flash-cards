#!/usr/bin/env python3


import pandas as pd
from pretty_cli import PrettyCli


def main() -> None:
    cli = PrettyCli()
    cli.main_title("Convert Data")

    # ================================================================ #
    cli.section("Loading Data")
    xl = pd.read_excel("Chinese language database _ 中文数据库.xlsx", sheet_name="All Characters (HSK 2.0)", usecols="B:O", skiprows=4, header=None)
    cli.print("Read OK")

    # ================================================================ #
    cli.section("Extracting Subset")

    subset = xl.loc[:, [2, 4, 10, 11, 14]]
    subset.columns = [ "level", "general_standard", "character", "pinyin", "translation" ]
    subset = subset.dropna()
    subset["level"] = subset["level"].astype(int)
    subset["general_standard"] = subset["general_standard"].astype(int)

    cli.print(subset)

    # ================================================================ #
    cli.section("Saving Data")
    subset.to_csv("hsk2.csv", index=False)
    cli.print("Write OK")

if __name__ == "__main__":
    main()
