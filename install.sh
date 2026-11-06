#!/bin/sh
# luge-edge installer — the headless Luge edge node.
#
#   curl -fsSL https://luge-works.github.io/luge-desktop-download/install.sh | sh
#
# Installs into ~/.local (override with LUGE_EDGE_PREFIX). The binaries live in a
# scoped dir (…/share/luge-edge) and only `luge-edge` is symlinked onto your PATH,
# so the bundled llama-server never pollutes it.
set -eu

BASE="https://luge-works.github.io/luge-desktop-download"
PREFIX="${LUGE_EDGE_PREFIX:-$HOME/.local}"

err() { echo "luge-edge install: $*" >&2; exit 1; }

# NB: quote the patterns — in `case`, an unquoted `|` is the OR operator, not a
# literal, so a space separator keeps the pattern a single literal token.
case "$(uname -s) $(uname -m)" in
  "Darwin arm64")   target="aarch64-apple-darwin" ;;
  "Linux x86_64")   target="x86_64-unknown-linux-gnu" ;;
  "Darwin x86_64")  err "Intel Macs aren't built yet — Apple Silicon only. See $BASE" ;;
  *)                err "no build for $(uname -s)/$(uname -m) yet. See $BASE" ;;
esac

command -v curl >/dev/null 2>&1 || err "curl is required"
command -v tar  >/dev/null 2>&1 || err "tar is required"

echo "Resolving the latest edge release…"
version="$(curl -fsSL "$BASE/edge-latest.json" | grep -o '"version"[^,]*' | head -1 | grep -o '[0-9][0-9.]*')"
[ -n "$version" ] || err "couldn't read the version from edge-latest.json"

url="$BASE/releases/edge/luge-edge-$version-$target.tar.gz"
share="$PREFIX/share/luge-edge"
bindir="$PREFIX/bin"
mkdir -p "$share" "$bindir"

echo "Downloading luge-edge $version ($target)…"
curl -fsSL "$url" | tar xz -C "$share" --strip-components=1
ln -sf "$share/luge-edge" "$bindir/luge-edge"

echo
echo "✓ Installed: $bindir/luge-edge"
"$bindir/luge-edge" --version 2>/dev/null || true
case ":$PATH:" in *":$bindir:"*) ;; *) echo "  ↳ add $bindir to your PATH" ;; esac
cat <<EOF

Next:
  luge-edge init      # connects to https://luge.tchatnsign.ai by default
  luge-edge pair      # open the printed URL on a signed-in device, approve
  luge-edge run       # or:  luge-edge service install   (run as a daemon)

  Custom / self-hosted Luge?  luge-edge config set api-url https://your-instance/api
EOF
