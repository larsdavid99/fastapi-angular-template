#!/usr/bin/env bash
# rename.sh — one-shot rename of the template placeholders to a new project name.
#
# Usage: ./bin/rename.sh my-new-app
#
# Replaces:
#   - "app" in package.json, angular.json, index.html, docker-compose container names
#   - Reads sed-style; does not touch .git, node_modules, .venv
set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <new-project-name>" >&2
    exit 1
fi

NEW_NAME="$1"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! [[ "$NEW_NAME" =~ ^[a-z][a-z0-9-]*$ ]]; then
    echo "Project name must be lowercase, start with a letter, and contain only a-z, 0-9, -" >&2
    exit 1
fi

echo "Renaming template placeholders to '$NEW_NAME' under $ROOT"

# Portable in-place sed (macOS / Linux)
sed_inplace() {
    if sed --version >/dev/null 2>&1; then
        sed -i "$@"
    else
        sed -i '' "$@"
    fi
}

# Container names in docker-compose.yml
sed_inplace "s/container_name: app-backend/container_name: ${NEW_NAME}-backend/" "$ROOT/docker-compose.yml"
sed_inplace "s/container_name: app-frontend/container_name: ${NEW_NAME}-frontend/" "$ROOT/docker-compose.yml"

# Angular project name in angular.json
sed_inplace "s/\"app\":/\"${NEW_NAME}\":/" "$ROOT/src/frontend/angular.json"
sed_inplace "s/\"app:build:production\"/\"${NEW_NAME}:build:production\"/" "$ROOT/src/frontend/angular.json"
sed_inplace "s/\"app:build:development\"/\"${NEW_NAME}:build:development\"/" "$ROOT/src/frontend/angular.json"

# Dockerfile production path
sed_inplace "s|/app/dist/app/browser|/app/dist/${NEW_NAME}/browser|" "$ROOT/src/frontend/Dockerfile"

# package.json name
sed_inplace "s/\"name\": \"app\"/\"name\": \"${NEW_NAME}\"/" "$ROOT/src/frontend/package.json"

# FastAPI title
sed_inplace "s/title=\"App API\"/title=\"${NEW_NAME} API\"/" "$ROOT/src/backend/main.py"
sed_inplace "s/\"Welcome to App API\"/\"Welcome to ${NEW_NAME} API\"/" "$ROOT/src/backend/main.py"

# index.html title
sed_inplace "s|<title>App</title>|<title>${NEW_NAME}</title>|" "$ROOT/src/frontend/src/index.html"

echo "Done. Next steps:"
echo "  1. cp .env.example src/backend/.env"
echo "  2. docker compose up --build"
