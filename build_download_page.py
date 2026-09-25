#!/usr/bin/env python3
"""Generate the public download page (index.html) for Luge — two tabs:

* Desktop — the installers mirrored under <releases_dir>/ (.dmg/.exe/.msi/.deb/.rpm).
* Edge    — the standalone CLI archives under <releases_dir>/edge/
            (luge-edge-<ver>-<target>.tar.gz / .zip), if any.

Run by the release workflows' deploy step, which copies the app icon to
luge-logo.png alongside the output. The 3-arg desktop call is unchanged; the
Edge tab renders from <releases_dir>/edge/ when present, else shows "coming soon".

Usage: build_download_page.py <desktop_version> <releases_dir> <out_html>
"""
import html
import os
import re
import sys

# Per-OS: (label, dashboard-icons name, [(ext, button label), …]). Icons come from
# homarr-labs/dashboard-icons via jsDelivr; rendered on a white chip so any logo
# (incl. the black Apple mark) stays visible on the dark page.
DESKTOP_GROUPS = [
    ("macOS", "apple", [(".dmg", "macOS (.dmg)")]),
    ("Windows", "windows-10", [(".exe", "Windows installer (.exe)"), (".msi", "Windows (.msi)")]),
    (
        "Linux",
        "linux",
        [
            (".AppImage", "Linux (AppImage)"),
            (".deb", "Debian / Ubuntu (.deb)"),
            (".rpm", "Fedora / RHEL (.rpm)"),
        ],
    ),
]

# Edge archives: (label, dashboard-icons name, Rust target triple in the filename).
EDGE_TARGETS = [
    ("macOS (Apple Silicon)", "apple", "aarch64-apple-darwin"),
    ("Linux (x86-64)", "linux", "x86_64-unknown-linux-gnu"),
    ("Windows (x86-64)", "windows-10", "x86_64-pc-windows-msvc"),
]

ICON_CDN = "https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/svg"

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Luge — Download</title>
<style>
  :root {
    --bg: #0b0b0d; --card: #16161a; --text: #f5f5f7; --muted: #9a9aa2;
    --accent: #dc2626; --border: #26262c;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--bg); color: var(--text); line-height: 1.5;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    -webkit-font-smoothing: antialiased;
  }
  .wrap { max-width: 880px; margin: 0 auto; padding: 8vh 24px 6vh; }
  .brand { display: flex; flex-direction: column; align-items: center; text-align: center; gap: 12px; }
  .brand img { width: 88px; height: 88px; border-radius: 20px; }
  h1 { margin: 0; font-size: 2rem; letter-spacing: -0.02em; }
  .lede { color: var(--muted); margin: 6px 0 0; max-width: 30rem; }
  .ver {
    display: inline-block; padding: 2px 12px; border-radius: 999px;
    border: 1px solid var(--border); color: var(--muted); font-size: 0.85rem;
  }
  /* CSS-only tabs: the radios live before the tabbar + panels as siblings. */
  input[name="tab"] { position: absolute; opacity: 0; pointer-events: none; }
  .tabbar { display: flex; justify-content: center; gap: 8px; margin-top: 40px; }
  .tabbar label {
    padding: 8px 20px; border-radius: 999px; border: 1px solid var(--border);
    color: var(--muted); cursor: pointer; font-weight: 600; font-size: 0.92rem;
  }
  #t-desktop:checked ~ .tabbar label[for="t-desktop"],
  #t-edge:checked ~ .tabbar label[for="t-edge"] {
    background: var(--accent); color: #fff; border-color: transparent;
  }
  .panel { display: none; }
  #t-desktop:checked ~ .panels .panel-desktop,
  #t-edge:checked ~ .panels .panel-edge { display: block; }
  .panels { margin-top: 16px; }
  .desc { text-align: center; color: var(--muted); margin: 14px auto 4px; max-width: 32rem; }
  .ver-line { text-align: center; margin-top: 12px; }
  .platforms { display: grid; gap: 16px; margin-top: 24px; }
  .card { background: var(--card); border: 1px solid var(--border); border-radius: 14px; padding: 18px 22px; }
  .card h2 { margin: 0 0 14px; font-size: 1.05rem; display: flex; align-items: center; }
  .os-icon {
    width: 30px; height: 30px; border-radius: 7px; background: #fff;
    padding: 5px; margin-right: 12px; flex: 0 0 auto;
  }
  .dls { display: flex; flex-wrap: wrap; gap: 10px; }
  .btn {
    display: inline-flex; align-items: center; padding: 10px 16px; border-radius: 10px;
    background: var(--accent); color: #fff; text-decoration: none; font-weight: 600;
    font-size: 0.92rem; border: 1px solid transparent;
  }
  .btn.alt { background: transparent; border-color: var(--border); color: var(--text); }
  .btn:hover { filter: brightness(1.08); }
  pre {
    background: #0e0e11; border: 1px solid var(--border); border-radius: 10px;
    padding: 14px 16px; font-size: 0.85rem; color: var(--text); margin-top: 18px;
    white-space: pre-wrap; overflow-wrap: anywhere;
  }
  code { background: #0e0e11; border: 1px solid var(--border); border-radius: 5px; padding: 1px 5px; font-size: 0.88em; }
  .cmd { position: relative; margin-top: 18px; }
  .cmd pre { margin: 0; padding-right: 56px; }
  .copy {
    position: absolute; top: 50%; right: 10px; transform: translateY(-50%);
    display: inline-flex; align-items: center; justify-content: center;
    width: 32px; height: 32px; padding: 0; cursor: pointer;
    background: transparent; border: 1px solid var(--border); border-radius: 8px;
    color: var(--muted);
  }
  .copy:hover { color: var(--text); border-color: var(--muted); }
  .copy.ok { color: #22c55e; border-color: #22c55e; }
  .soon { color: var(--muted); text-align: center; padding: 32px 0; }
  footer { text-align: center; margin-top: 48px; color: var(--muted); font-size: 0.85rem; }
  footer a { color: var(--muted); }
</style>
</head>
<body>
  <div class="wrap">
    <header class="brand">
      <img src="luge-logo.png" alt="Luge" />
      <div><h1>Luge</h1></div>
      <p class="lede">Two ways to run Luge on your machine — pick a tab.</p>
    </header>

    <input type="radio" name="tab" id="t-desktop" checked />
    <input type="radio" name="tab" id="t-edge" />
    <div class="tabbar">
      <label for="t-desktop">Desktop app</label>
      <label for="t-edge">Edge node</label>
    </div>

    <div class="panels">
      <section class="panel panel-desktop">
        <p class="desc">The full Luge app for your computer — it records and summarizes
        your meetings automatically, and updates itself. Install and sign in.</p>
        <div class="ver-line"><span class="ver">Desktop __DESKTOP_VERSION__</span></div>
        <div class="platforms">
__DESKTOP_CARDS__
        </div>
      </section>
      <section class="panel panel-edge">
__EDGE_BODY__
      </section>
    </div>

    <footer>
      <a href="https://github.com/luge-works/luge-desktop-download">releases repo</a>
      &middot; <a href="latest.json">latest.json</a>
    </footer>
  </div>
</body>
</html>
"""

EDGE_DESC = """        <p class="desc">A headless node you run on a server or a spare machine — no UI.
        It serves that machine's local tools and on-device inference to your Luge
        agents. Pair it once, then it runs in the background.</p>"""

EDGE_INSTALL = """        <p class="desc"><strong>macOS &amp; Linux — one line:</strong></p>
        <div class="cmd">
          <pre>curl -fsSL https://luge-works.github.io/luge-desktop-download/install.sh | sh</pre>
          <button class="copy" type="button" title="Copy" aria-label="Copy command" onclick="navigator.clipboard.writeText(this.parentElement.querySelector('pre').textContent.trim());this.classList.add('ok');setTimeout(()=>this.classList.remove('ok'),1200)"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg></button>
        </div>
        <p class="desc">It prints the next steps when it's done. Windows: download the <code>.zip</code> below.</p>"""


def card(title, icon, buttons):
    img = f'<img class="os-icon" src="{ICON_CDN}/{icon}.svg" alt="" />' if icon else ""
    return (
        f'          <section class="card"><h2>{img}{title}</h2>\n'
        f'            <div class="dls">{"".join(buttons)}</div>\n'
        f"          </section>"
    )


def build_desktop_cards(files):
    cards = []
    for os_name, icon, exts in DESKTOP_GROUPS:
        buttons = []
        for ext, label in exts:
            for name in (f for f in files if f.endswith(ext)):
                cls = "btn" if not buttons else "btn alt"
                href = "releases/desktop/" + html.escape(name, quote=True)
                buttons.append(f'<a class="{cls}" href="{href}">{html.escape(label)}</a>')
        if buttons:
            cards.append(card(os_name, icon, buttons))
    return "\n".join(cards)


def _semver(v):
    """(major, minor, patch) for ordering; non-numeric chars stripped per part."""
    parts = (v.split(".") + ["0", "0", "0"])[:3]
    return tuple(int("".join(c for c in p if c.isdigit()) or 0) for p in parts)


def edge_version(files):
    """The LATEST edge version among the archives. The deploy keeps only the
    current release, but pick the max as a safety net so a stray older archive
    can never pin the page to an old version."""
    versions = set()
    for name in files:
        m = re.match(r"luge-edge-(.+?)-(?:aarch64|x86_64)-", name)
        if m:
            versions.add(m.group(1))
    return max(versions, key=_semver) if versions else None


def build_edge_body(files):
    ver = edge_version(files)
    if ver is None:
        return f'{EDGE_DESC}\n        <p class="soon">Edge builds are coming soon.</p>'
    # Only the latest version's archives (defensive: the deploy already prunes
    # older releases, but guard against a stray leftover).
    latest = [f for f in files if f"luge-edge-{ver}-" in f]
    cards = []
    for label, icon, triple in EDGE_TARGETS:
        for name in latest:
            if triple in name and (name.endswith(".tar.gz") or name.endswith(".zip")):
                href = "releases/edge/" + html.escape(name, quote=True)
                cards.append(card(label, icon, [f'<a class="btn" href="{href}">Download</a>']))
                break
    if not cards:
        return f'{EDGE_DESC}\n        <p class="soon">Edge builds are coming soon.</p>'
    return (
        f"{EDGE_DESC}\n"
        f'        <div class="ver-line"><span class="ver">Edge {html.escape(ver)}</span></div>\n'
        f"{EDGE_INSTALL}\n"
        f'        <div class="platforms">\n' + "\n".join(cards) + "\n        </div>"
    )


def main():
    if len(sys.argv) != 4:
        sys.exit("usage: build_download_page.py <desktop_version> <releases_dir> <out_html>")
    version, releases_dir, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    # Each product owns a subdir so the two deploys never clobber each other:
    # releases/desktop/ (installers) and releases/edge/ (CLI archives).
    desktop_dir = os.path.join(releases_dir, "desktop")
    desktop_files = sorted(os.listdir(desktop_dir)) if os.path.isdir(desktop_dir) else []
    desktop_cards = build_desktop_cards(desktop_files)
    if not desktop_cards:
        sys.exit(f"no installers found in {desktop_dir}")
    edge_dir = os.path.join(releases_dir, "edge")
    edge_files = sorted(os.listdir(edge_dir)) if os.path.isdir(edge_dir) else []
    page = (
        PAGE.replace("__DESKTOP_VERSION__", html.escape(version))
        .replace("__DESKTOP_CARDS__", desktop_cards)
        .replace("__EDGE_BODY__", build_edge_body(edge_files))
    )
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"wrote {out_path} (desktop: {len(desktop_files)} assets, edge: {len(edge_files)} assets)")


if __name__ == "__main__":
    main()
