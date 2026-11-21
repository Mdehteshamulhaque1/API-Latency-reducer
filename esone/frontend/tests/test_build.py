"""The static build (used for Vercel) produces the same pages as the dev server."""
import sys
from pathlib import Path

FRONTEND_DIR = Path(__file__).resolve().parents[1]
if str(FRONTEND_DIR) not in sys.path:
    sys.path.insert(0, str(FRONTEND_DIR))

from build import build  # noqa: E402

from esone_web.main import PAGES  # noqa: E402


def test_build_writes_every_page_with_api_url_and_assets(tmp_path):
    out = tmp_path / "dist"
    written = build(out, "https://esone-api.example.com")

    expected = {"index.html", "login.html", "register.html", "chat.html", "account.html", "admin.html"}
    assert {p.name for p in written} == expected
    assert len(PAGES) == len(expected)

    for html_file in written:
        html = html_file.read_text(encoding="utf-8")
        assert '<meta name="esone-api-url" content="https://esone-api.example.com">' in html
        assert "{{" not in html and "{%" not in html, f"unrendered template syntax in {html_file.name}"
        assert 'src="/static/js/site.js?v=' in html

    assert (out / "static" / "css" / "app.css").is_file()
    for name in ("site", "api", "dom", "home", "searchbar", "login", "register", "chat", "account", "admin"):
        assert (out / "static" / "js" / f"{name}.js").is_file()


def test_build_replaces_a_previous_output(tmp_path):
    out = tmp_path / "dist"
    out.mkdir()
    (out / "stale.html").write_text("old", encoding="utf-8")
    build(out, "https://esone-api.example.com")
    assert not (out / "stale.html").exists()
    assert (out / "index.html").exists()
