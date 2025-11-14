"""CLI to search IDX announcements API using keywords and save results."""

import argparse
from scraper.idx_api import (
    fetch_matching_announcements,
    DEFAULT_KEYWORDS,
    session_from_playwright_interactive,
)
from scraper.utils import save_json, save_csv, save_excel


def main():
    p = argparse.ArgumentParser(description="Search IDX announcements by keywords")
    p.add_argument("--output", required=True, help="Output path (.json/.csv/.xlsx)")
    p.add_argument(
        "--max-pages", type=int, default=10, help="Limit pages fetched (for testing)"
    )
    p.add_argument("--date-from", default="19010101")
    p.add_argument("--date-to", default="20250920")
    p.add_argument("--page-size", type=int, default=100)
    p.add_argument(
        "--keywords", nargs="*", help="Optional keywords to override built-in list"
    )
    p.add_argument(
        "--interactive",
        action="store_true",
        help="Open browser to solve challenges and capture session cookies",
    )

    args = p.parse_args()

    keywords = args.keywords if args.keywords else DEFAULT_KEYWORDS

    sess = None
    if args.interactive:
        sess = session_from_playwright_interactive()

    results = list(
        fetch_matching_announcements(
            keywords,
            date_from=args.date_from,
            date_to=args.date_to,
            page_size=args.page_size,
            max_pages=args.max_pages,
            session=sess,
        )
    )

    out = args.output
    if out.lower().endswith(".json"):
        save_json(results, out)
    elif out.lower().endswith(".csv"):
        # flatten minimal fields for CSV
        flat = []
        for r in results:
            peng = r.get("pengumuman") or {}
            row = {
                "Id2": peng.get("Id2"),
                "NoPengumuman": peng.get("NoPengumuman"),
                "TglPengumuman": peng.get("TglPengumuman"),
                "JudulPengumuman": peng.get("JudulPengumuman"),
                "Kode_Emiten": (peng.get("Kode_Emiten") or "").strip(),
            }
            flat.append(row)
        save_csv(flat, out)
    elif out.lower().endswith((".xls", ".xlsx")):
        save_excel([r.get("pengumuman") or {} for r in results], out)
    else:
        print("Unknown output format. Use .json, .csv, .xls or .xlsx")


if __name__ == "__main__":
    main()
