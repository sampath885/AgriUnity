"""
Utility to split a very large CSV into multiple smaller CSV files.

Each output file includes the header row so it is independently processable.

Usage (from repo root on Windows PowerShell):
  python farmers/agriunity-project/backend/scripts/split_csv.py \
    --source farmers/agriunity-project/backend/data/Agriculture_price_dataset.csv \
    --rows-per-file 700000 \
    --output-dir farmers/agriunity-project/backend/data/parts
"""

from __future__ import annotations

import os
import argparse
import pandas as pd


def split_csv(source_file: str, rows_per_file: int, output_dir: str) -> None:
    os.makedirs(output_dir, exist_ok=True)
    reader = pd.read_csv(source_file, chunksize=rows_per_file, low_memory=False)

    for i, chunk in enumerate(reader):
        output_filename = os.path.join(output_dir, f"data_part_{i+1}.csv")
        print(f"Saving {output_filename}...")
        # Always include header so each part is self-contained
        chunk.to_csv(output_filename, index=False)
    print("Done splitting.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Split a large CSV into smaller parts.")
    parser.add_argument("--source", required=True, help="Path to the large source CSV file")
    parser.add_argument("--rows-per-file", type=int, default=700000, help="Rows per output file (default: 700000)")
    parser.add_argument("--output-dir", required=True, help="Directory to write the part files into")
    args = parser.parse_args()

    split_csv(args.source, args.rows_per_file, args.output_dir)


if __name__ == "__main__":
    main()


