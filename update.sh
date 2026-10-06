#!/usr/bin/env bash
# Apply a new version of the project from a zip, then show what changed.
#
#   cd ~/reflection
#   ./update.sh /mnt/c/Users/INTEL/Downloads/reflection_step4.zip
#
# It updates the project you are standing in (the git repository of the
# current directory), not the folder the script lives in. So it can also be
# installed as a command, e.g. copied to $CONDA_PREFIX/bin/rfl-update.
#
# 1. refuses to run if you have uncommitted changes (so the update is one clean diff)
# 2. unpacks the zip into a temp folder and copies it over the project
# 3. lists files that are in the project but not in the zip (maybe removed upstream)
# 4. runs the tests
# Nothing is committed: look at `git diff`, then commit yourself.
set -euo pipefail

# your own files that never come in the zip: not reported as stale
KEEP=(README.md ROADMAP.md)

# The whole script is one function, read by bash before it runs, so it can
# safely overwrite itself when the zip contains a newer update.sh.
main() {
    zip="${1:-}"
    if [[ -z "$zip" || ! -f "$zip" ]]; then
        echo "usage: update.sh path/to/reflection_stepN.zip   (run it inside the project)" >&2
        exit 2
    fi
    zip="$(realpath "$zip")"

    # the project = the git repository we are standing in; refuse anything else
    if ! root="$(git rev-parse --show-toplevel 2>/dev/null)"; then
        echo "Not inside a git repository. cd into the project first (cd ~/reflection)." >&2
        exit 1
    fi
    if [[ ! -f "$root/Project.py" || ! -d "$root/Engine" ]]; then
        echo "$root does not look like the reflection project (no Project.py / Engine)." >&2
        exit 1
    fi
    cd "$root"
    echo "updating $root"

    if [[ -n "$(git status --porcelain)" ]]; then
        echo "You have uncommitted changes. Commit or stash them first:" >&2
        git status --short >&2
        exit 1
    fi

    tmp="$(mktemp -d)"
    trap 'rm -rf "$tmp"' EXIT
    unzip -q "$zip" -d "$tmp"
    src="$tmp/reflection"
    [[ -d "$src" ]] || src="$tmp"          # zip without a top-level reflection/ folder

    cp -r "$src"/. .
    rm -rf sim_build .pytest_cache
    find . -name __pycache__ -type d -prune -exec rm -rf {} +

    echo
    echo "== files in the project but not in the zip (delete them if they were removed):"
    stale=0
    while IFS= read -r f; do
        [[ " ${KEEP[*]} " == *" $f "* ]] && continue
        if [[ ! -e "$src/$f" ]]; then
            echo "   $f"
            stale=1
        fi
    done < <(git ls-files)
    [[ $stale == 0 ]] && echo "   (none)"

    echo
    echo "== what changed:"
    git status --short

    echo
    echo "== tests:"
    python -m pytest tests -q || true

    echo
    echo "Check 'git diff', delete stale files if needed, then:"
    echo "   git add -A && git commit -m \"...\""
}

main "$@"
exit
