"""Render the Esone pages to static HTML for Vercel (or any static host).

The pages are static apart from the API address, so instead of running the
FastAPI server in production we render every template once at build time and
copy the CSS and compiled JS next to it. The output in ``dist/`` is a plain
website:

    dist/
    ├── index.html, login.html, register.html, account.html, admin.html
    └── static/css/app.css, static/js/*.js

Usage:
    ESONE_WEB_API_URL=https://esone-api.onrender.com python build.py [--out dist]

The same templates, settings and page table are used by ``esone_web.main``,
so the local dev server and the static build cannot drift apart.
"""
from __future__ import annotations

import argparse
import shutil
from datetime import UTC, datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from esone_web.main import ASSET_VERSION, PAGES, STATIC_DIR, TEMPLATES_DIR, get_settings


def _url_for(name: str, path: str = "") -> str:
    """Stand-in for Starlette's url_for; only the static mount is used by the templates."""
    if name != "static":
        raise ValueError(f"url_for({name!r}) is not available in the static build")
    return f"/static/{path}"


def build(out: Path, api_url: str) -> list[Path]:
    """Write the site into ``out`` (replacing it) and return the HTML files written."""
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True)
    env.globals["url_for"] = _url_for

    # Clear the contents rather than deleting the folder itself: on Windows a
    # shell or preview server sitting inside ``out`` would otherwise block the build.
    out.mkdir(parents=True, exist_ok=True)
    for child in out.iterdir():
        shutil.rmtree(child) if child.is_dir() else child.unlink()
    shutil.copytree(STATIC_DIR, out / "static")

    context = {
        "api_url": api_url,
        "asset_version": ASSET_VERSION,
        "year": datetime.now(UTC).year,
    }
    written: list[Path] = []
    for page, (path, template) in PAGES.items():
        html = env.get_template(template).render(page=page, **context)
        target = out / ("index.html" if path == "/" else f"{path.strip('/')}.html")
        target.write_text(html, encoding="utf-8")
        written.append(target)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parent / "dist")
    parser.add_argument("--api-url", default=None, help="overrides ESONE_WEB_API_URL")
    args = parser.parse_args()

    api_url = args.api_url or get_settings().api_url
    written = build(args.out, api_url)
    print(f"API URL: {api_url}")
    for path in written:
        print(f"  {path.relative_to(args.out.parent)}")
    print(f"static assets copied to {args.out / 'static'}")


if __name__ == "__main__":
    main()
