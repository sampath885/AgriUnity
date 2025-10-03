"""
High-throughput parallel ingestion for a very large CSV.

Steps performed:
  1) Split the source CSV into many smaller parts (with headers)
  2) Launch multiple parallel workers, each processing one part via
     scripts/process_single_file.py

Usage (from repo root on Windows PowerShell):
  # Activate venv, then run:
  python farmers/agriunity-project/backend/scripts/parallel_ingest.py \
    --source farmers/agriunity-project/backend/scripts/BIG_DATA.csv \
    --rows-per-file 350000 \
    --workers 20

Environment variables (inherited by workers):
  GOOGLE_API_KEY, CSV_PANDAS_CHUNK_SIZE, CSV_EMBED_BATCH_SIZE,
  CSV_DATE_CUTOFF_DAYS, CSV_USE_MONTHLY_AGGREGATION, CSV_SAMPLE_EVERY_N
"""

from __future__ import annotations

import os
import sys
import argparse
import subprocess
import time
from typing import List


def split_csv(source_file: str, rows_per_file: int, output_dir: str) -> List[str]:
    os.makedirs(output_dir, exist_ok=True)
    # Import lazily to avoid importing pandas unless needed here
    import pandas as pd

    part_paths: List[str] = []
    reader = pd.read_csv(source_file, chunksize=rows_per_file, low_memory=False)
    for i, chunk in enumerate(reader):
        output_filename = os.path.join(output_dir, f"data_part_{i+1}.csv")
        print(f"Saving {output_filename}...")
        chunk.to_csv(output_filename, index=False)
        part_paths.append(output_filename)
    print(f"Done splitting into {len(part_paths)} parts.")
    return part_paths


def run_in_parallel(part_files: List[str], workers: int) -> None:
    """Run at most 'workers' child processes concurrently until all parts finish."""
    script_path = os.path.join(
        os.path.dirname(__file__),
        "process_single_file.py",
    )

    remaining = list(part_files)
    running: List[subprocess.Popen] = []

    def start_next() -> None:
        if not remaining:
            return
        next_file = remaining.pop(0)
        print(f"Starting worker for: {next_file}")
        # Ensure child process runs in backend/ so Django can resolve 'core.settings'
        backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        # Inherit stdout/stderr so child logs stream directly to this console
        p = subprocess.Popen(
                [sys.executable, script_path, "--csv", next_file],
                cwd=backend_dir,
                env=os.environ.copy(),
                stdout=None,
                stderr=None,
                text=True,
            )
        p._agriunity_file = next_file  # type: ignore[attr-defined]
        running.append(p)

    # Fill initial slots
    for _ in range(min(workers, len(remaining))):
        start_next()

    # Poll running processes and report completion
    while running:
        time.sleep(0.5)
        for p in list(running):
            ret = p.poll()
            if ret is not None:
                part = getattr(p, "_agriunity_file", "<unknown>")
                if ret == 0:
                    print(f"Worker completed successfully: {part}")
                else:
                    print(f"Worker failed (exit={ret}): {part}")
                running.remove(p)
                # Start another if any remaining
                start_next()


def main() -> None:
    parser = argparse.ArgumentParser(description="Parallel ingestion orchestrator for large CSV")
    parser.add_argument(
        "--source",
        required=False,
        help="Path to the large source CSV file (e.g., backend/scripts/BIG_DATA.csv). If omitted, will try to auto-detect a single CSV in scripts/.",
    )
    parser.add_argument("--rows-per-file", type=int, default=350000, help="Rows per split file (default: 350000)")
    parser.add_argument("--workers", type=int, default=20, help="Number of parallel worker processes")
    parser.add_argument(
        "--output-dir",
        default=os.path.join(os.path.dirname(__file__), "parts"),
        help="Directory to store split part files (default: backend/scripts/parts)",
    )

    args = parser.parse_args()

    # Recommended env settings for ~1 hour target (tune as needed)
    os.environ.setdefault("CSV_PANDAS_CHUNK_SIZE", "200000")
    os.environ.setdefault("CSV_EMBED_BATCH_SIZE", "1024")
    os.environ.setdefault("CSV_USE_MONTHLY_AGGREGATION", "1")
    os.environ.setdefault("CSV_SAMPLE_EVERY_N", "1")

    # Resolve source path; allow auto-detection if not provided or incorrect
    scripts_dir = os.path.dirname(__file__)
    chosen_source = None

    if args.source:
        candidate = os.path.abspath(args.source)
        if not os.path.exists(candidate):
            # Try resolving relative to scripts directory
            alt = os.path.join(scripts_dir, os.path.basename(args.source))
            if os.path.exists(alt):
                chosen_source = os.path.abspath(alt)
        else:
            chosen_source = candidate

    if chosen_source is None:
        # Auto-detect CSV in scripts dir
        csvs = [f for f in os.listdir(scripts_dir) if f.lower().endswith('.csv')]
        if len(csvs) == 1:
            chosen_source = os.path.join(scripts_dir, csvs[0])
            print(f"Auto-detected CSV: {chosen_source}")
        elif len(csvs) > 1:
            print("Multiple CSV files found in scripts directory. Please specify one via --source. Found:")
            for f in csvs:
                print(f" - {os.path.join(scripts_dir, f)}")
            sys.exit(1)
        else:
            print("No CSV file found. Provide --source pointing to your big CSV (e.g., backend/scripts/BIG_DATA.csv).")
            sys.exit(1)

    part_files = split_csv(chosen_source, args.rows_per_file, args.output_dir)
    if not part_files:
        print("No part files created. Check source path.")
        return

    run_in_parallel(part_files, args.workers)
    print("All workers finished.")


if __name__ == "__main__":
    main()


