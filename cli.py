"""CLI for running the scraper.

Example usage:
    python cli.py --url https://example.com --row-selector "table tr" --header-selector "table thead tr" --output out.xlsx
"""

import argparse
from scraper.scraper import scrape
from scraper.utils import save_json, save_csv, save_excel


def main():
    p = argparse.ArgumentParser(description="Simple scraper CLI")
    p.add_argument("--url", required=True, help="URL to scrape")
    p.add_argument(
        "--row-selector", required=True, help="CSS selector for rows (e.g., 'table tr')"
    )
    p.add_argument(
        "--header-selector",
        required=False,
        help="CSS selector for header row (e.g., 'table thead tr')",
    )
    p.add_argument("--output", required=True, help="Output path (json/csv/xlsx)")
    p.add_argument(
        "--no-playwright",
        dest="prefer_playwright",
        action="store_false",
        help="Disable Playwright and use requests fallback",
    )
    args = p.parse_args()

    rows = scrape(
        args.url,
        args.row_selector,
        args.header_selector,
        prefer_playwright=args.prefer_playwright,
    )

    out = args.output
    if out.lower().endswith(".json"):
        save_json(rows, out)
    elif out.lower().endswith(".csv"):
        save_csv(rows, out)
    elif out.lower().endswith((".xls", ".xlsx")):
        save_excel(rows, out)
    else:
        print("Unknown output format. Use .json, .csv, .xls or .xlsx")


if __name__ == "__main__":
    main()
