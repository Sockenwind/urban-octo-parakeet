#!/usr/bin/env python3
"""Build a single self-contained HTML file of the game (all scripts inlined).

Usage (from the mrs-anthrope-game folder):  python3 tools/build_single.py
Writes retropie/mrs-anthrope.html - handy for RetroPie, USB sticks or sending the game as one file.
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "retropie", "mrs-anthrope.html")


def main():
    html = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()

    def inline(m):
        src = m.group(1)
        code = open(os.path.join(ROOT, src), encoding="utf-8").read()
        return "<script>/* " + src + " */\n" + code.replace("</script", "<\\/script") + "\n</script>"

    html, n = re.subn(r'<script src="(js/[^"]+)"></script>', inline, html)
    assert n == 4, "expected 4 external scripts, found %d" % n
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print("wrote", OUT, os.path.getsize(OUT), "bytes")


if __name__ == "__main__":
    main()
