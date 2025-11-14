#!/usr/bin/env python3
"""Interactive helper to create a local .env file for idx-scraper.

This script prompts for IDX_AUTH_EMAIL, IDX_AUTH_PASSWORD, IDX_AUTH_TOKEN and IDX_PROXY
and writes them to a `.env` file in the current directory. It will not overwrite an
existing `.env` unless explicitly asked.
"""

from __future__ import annotations

import getpass
from pathlib import Path


def prompt(prompt_text: str, default: str = "") -> str:
    v = input(f"{prompt_text}" + (f" [{default}]" if default else "") + ": ")
    if not v.strip():
        return default
    return v.strip()


def main() -> None:
    out = Path(".env")
    if out.exists():
        resp = input(".env already exists. Overwrite? [y/N]: ")
        if resp.strip().lower() not in ("y", "yes"):
            print("Aborted. .env not changed.")
            return

    print(
        "This helper will create a .env file with IDX_AUTH_EMAIL and IDX_AUTH_PASSWORD."
    )
    email = prompt("IDX_AUTH_EMAIL")
    if not email:
        print("No email provided — exiting.")
        return
    pw = getpass.getpass("IDX_AUTH_PASSWORD: ")
    token = prompt("IDX_AUTH_TOKEN (optional)")
    proxy = prompt("IDX_PROXY (optional)")

    lines = []
    lines.append(f"IDX_AUTH_EMAIL={email}")
    lines.append(f"IDX_AUTH_PASSWORD={pw}")
    if token:
        lines.append(f"IDX_AUTH_TOKEN={token}")
    if proxy:
        lines.append(f"IDX_PROXY={proxy}")

    # write with restricted perms where possible
    text = "\n".join(lines) + "\n"
    try:
        # atomic-ish write
        tmp = out.with_suffix(".env.tmp")
        tmp.write_text(text, encoding="utf-8")
        try:
            tmp.chmod(0o600)
        except Exception:
            pass
        tmp.replace(out)
        try:
            out.chmod(0o600)
        except Exception:
            pass
        print(
            f"Wrote .env to {out} (mode 600 where supported). Do NOT commit this file to git."
        )
    except Exception as e:
        print("Failed to write .env:", e)


if __name__ == "__main__":
    main()
