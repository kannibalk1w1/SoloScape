#!/bin/sh
# SoloScape installer: one file that is both this shell script and a Python zipapp (the program follows below).
#
#   sh soloscape-installer.sh --plan        # what it will download and install
#   sh soloscape-installer.sh --cache ~/Downloads/2026-08-02-void-634-cache.7z
#
# A computer without Python 3 and git (a stock Steam Deck, for example) first gets pinned copies of both, installed into
# the SoloScape folder only, with no root access. Each file is downloaded over HTTPS and checked against the SHA-256
# recorded below before anything is installed; nothing else on the computer is changed.
set -eu
self=$0
case "$self" in /*) ;; *) self=$PWD/$self ;; esac
data=
prev=
plan=no
yes=no
for arg in "$@"; do
    [ "$prev" = --data ] && data=$arg
    case "$arg" in --data=*) data=${arg#--data=} ;; --plan) plan=yes ;; --yes) yes=yes ;; esac
    prev=$arg
done
[ -n "$data" ] || data=${XDG_DATA_HOME:-$HOME/.local/share}/soloscape
case "$data" in /*) ;; *) data=$PWD/$data ;; esac
envdir=$data/tools/env

if [ -x "$envdir/bin/python3" ] && [ -x "$envdir/bin/git" ]; then
    PATH=$envdir/bin:$PATH
    export PATH
    exec python3 "$self" "$@"
fi
if command -v python3 >/dev/null 2>&1 && command -v git >/dev/null 2>&1 &&
    python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
    exec python3 "$self" "$@"
fi

if [ "$(uname -s)" != Linux ] || [ "$(uname -m)" != x86_64 ]; then
    echo "SoloScape installer: this installer supports Linux x86_64 (including Steam Deck) only." >&2
    exit 2
fi
for tool in curl sha256sum; do
    command -v "$tool" >/dev/null 2>&1 || { echo "SoloScape installer: '$tool' is needed to set up Python and git and was not found." >&2; exit 2; }
done

cat <<TEXT
This computer has no usable Python 3 and git, which the installer needs. It will set up pinned copies of both
(about @@TOTAL_MB@@ MB from conda-forge, via the micromamba program from github.com/mamba-org) inside
$data/tools, with no root access and nothing changed elsewhere. Every file is checked against a pinned SHA-256 first.
TEXT
if [ "$plan" = yes ]; then
    echo "Run again without --plan to continue; the full plan (Java, source, cache) is shown after this step."
    exit 0
fi
if [ "$yes" != yes ]; then
    if [ -t 0 ]; then
        printf 'Continue? [y/N] '
        read -r answer
        case "$answer" in y | Y | yes | YES) ;; *) echo "Nothing was changed."; exit 0 ;; esac
    else
        echo "SoloScape installer: run with --yes to confirm the step above (no terminal to ask)." >&2
        exit 2
    fi
fi

downloads=$data/downloads/tools
mkdir -p "$downloads"
fetch() { # url sha256 destination
    if [ -f "$3" ] && [ "$(sha256sum "$3" | cut -d' ' -f1)" = "$2" ]; then return 0; fi
    echo "Downloading $(basename "$3") ..."
    curl --fail --location --silent --show-error --retry 3 --connect-timeout 30 --max-time 1800 \
        --proto '=https' --proto-redir '=https' -o "$3.part" "$1" ||
        { rm -f "$3.part"; echo "SoloScape installer: could not download $1. Check the connection and run it again; finished downloads are kept." >&2; exit 2; }
    if [ "$(sha256sum "$3.part" | cut -d' ' -f1)" != "$2" ]; then
        rm -f "$3.part"
        echo "SoloScape installer: $1 did not match its pinned hash and was discarded. Nothing was installed from it." >&2
        exit 2
    fi
    mv "$3.part" "$3"
}

mamba=$downloads/micromamba
fetch '@@MICROMAMBA_URL@@' '@@MICROMAMBA_SHA@@' "$mamba"
chmod 755 "$mamba"
spec=$downloads/environment.explicit
echo '@EXPLICIT' > "$spec"
while read -r sha url; do
    [ -n "$sha" ] || continue
    file=$downloads/${url##*/}
    fetch "$url" "$sha" "$file"
    echo "$file" >> "$spec"
done <<LOCK
@@LOCK@@
LOCK
echo "Installing Python and git ..."
rm -rf "$envdir"
mkdir -p "$data/tools"
MAMBA_ROOT_PREFIX=$data/tools/mamba "$mamba" create -y -q -p "$envdir" --no-rc --offline -f "$spec" ||
    { rm -rf "$envdir"; echo "SoloScape installer: setting up Python and git failed. Nothing else was changed." >&2; exit 2; }
if ! "$envdir/bin/python3" -c 'import sys' || ! "$envdir/bin/git" --version >/dev/null; then
    rm -rf "$envdir"
    echo "SoloScape installer: the Python and git setup did not work. Nothing else was changed." >&2
    exit 2
fi
PATH=$envdir/bin:$PATH
export PATH
exec python3 "$self" "$@"
exit 1
