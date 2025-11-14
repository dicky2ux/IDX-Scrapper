"""Utility functions for saving scraped data to JSON, CSV, and Excel."""
from typing import List, Dict
import json
import pandas as pd


def save_json(rows: List[Dict], path: str, indent: int = 2) -> None:
    """Save list of dicts to a JSON file."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=indent)


def save_csv(rows: List[Dict], path: str) -> None:
    """Save list of dicts to CSV using pandas to handle unicode and proper quoting."""
    if not rows:
        # create empty dataframe
        df = pd.DataFrame()
    else:
        df = pd.DataFrame(rows)
    df.to_csv(path, index=False)


def save_excel(rows: List[Dict], path: str) -> None:
    """Save list of dicts to an Excel file using openpyxl engine."""
    if not rows:
        df = pd.DataFrame()
    else:
        df = pd.DataFrame(rows)
    df.to_excel(path, index=False)
