"""
Standalone script to process a single CSV file into knowledge chunks.

This reuses the production-grade logic from chatbot.knowledge_base_manager, but
avoids the watcher and runs in a plain Python process so you can launch many in parallel.

Usage (from repo root on Windows PowerShell):
  # Activate venv first
  # Then run:
  python farmers/agriunity-project/backend/scripts/process_single_file.py \
    --csv farmers/agriunity-project/backend/data/parts/data_part_1.csv

Environment variables honored (same as watcher):
  GOOGLE_API_KEY
  CSV_PANDAS_CHUNK_SIZE
  CSV_EMBED_BATCH_SIZE
  CSV_DATE_CUTOFF_DAYS
  CSV_USE_MONTHLY_AGGREGATION
  CSV_SAMPLE_EVERY_N
"""

from __future__ import annotations

import os
import argparse
import sys
import django


def setup_django() -> None:
    # Configure Django settings to use the same DB/models
    base_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.abspath(os.path.join(base_dir, ".."))  # move to backend/
    # Ensure backend dir is on sys.path so 'core' and apps are importable
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    os.chdir(backend_dir)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
    django.setup()


def main() -> None:
    parser = argparse.ArgumentParser(description="Process a single CSV file into knowledge chunks.")
    parser.add_argument("--csv", required=True, help="Path to the CSV file to process")
    args = parser.parse_args()

    setup_django()

    from chatbot.knowledge_base_manager import process_large_csv_in_batches

    file_path = os.path.abspath(args.csv)
    print(f"Processing file: {file_path}")
    total = process_large_csv_in_batches(file_path)
    print(f"Completed. Total chunks saved: {total}")


if __name__ == "__main__":
    main()


