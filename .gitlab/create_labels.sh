#!/usr/bin/env bash
# Seed labels in GitLab from .gitlab/labels.json
# Usage: GL_TOKEN=xxx GL_PROJECT_ID=123456 ./create_labels.sh
set -euo pipefail

if [[ -z "${GL_TOKEN:-}" || -z "${GL_PROJECT_ID:-}" ]]; then
  echo "Bitte GL_TOKEN und GL_PROJECT_ID exportieren."
  exit 1
fi

BASE_URL="${GL_API_URL:-https://gitlab.com/api/v4}"
LABELS_FILE="$(dirname "$0")/labels.json"

if [[ ! -f "$LABELS_FILE" ]]; then
  echo "labels.json nicht gefunden unter $LABELS_FILE"
  exit 1
fi

python - <<'PY'
import json, os, subprocess, sys

token = os.environ.get("GL_TOKEN")
project = os.environ.get("GL_PROJECT_ID")
base = os.environ.get("GL_API_URL", "https://gitlab.com/api/v4")
labels_file = os.path.join(os.path.dirname(__file__), "labels.json")

if not token or not project:
    sys.exit("GL_TOKEN oder GL_PROJECT_ID fehlt")

with open(labels_file, "r", encoding="utf-8") as f:
    labels = json.load(f)

for label in labels:
    name = label["name"]
    color = label["color"]
    desc = label.get("description", "")
    cmd = [
        "curl",
        "-sS",
        "--header",
        f"PRIVATE-TOKEN: {token}",
        "--data-urlencode",
        f"name={name}",
        "--data-urlencode",
        f"color={color}",
        "--data-urlencode",
        f"description={desc}",
        "-X",
        "POST",
        f"{base}/projects/{project}/labels",
    ]
    subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL)
    print(f"Label angelegt/aktualisiert: {name}")
PY
