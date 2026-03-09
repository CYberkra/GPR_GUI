#!/usr/bin/env bash
set -euo pipefail

REPO_GPR="/mnt/e/Openclaw/.openclaw/workspace/repos/GPR_GUI"
REPO_PUB="/mnt/e/Openclaw/.openclaw/workspace/tmp/temp_repository"

EXE="$REPO_GPR/dist/GPR_GUI_Qt.exe"
TARGET="$REPO_PUB/releases/GPR_GUI_Qt.exe"

[[ -f "$EXE" ]] || { echo "missing exe: $EXE"; exit 1; }
mkdir -p "$REPO_PUB/releases"
cp -f "$EXE" "$TARGET"

cd "$REPO_PUB"
git add releases/GPR_GUI_Qt.exe
if git diff --cached --quiet; then
  echo "No release change to commit."
  exit 0
fi

git commit -m "build: refresh GPR_GUI_Qt.exe"
git pull --rebase origin main
git push origin main

echo "Published: $(git rev-parse --short HEAD)"
