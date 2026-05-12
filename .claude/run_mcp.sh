#!/usr/bin/env bash
# Resolve repo root from this script's location so this works from any clone.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec uv run --project "$REPO_ROOT" site-scraper-mcp "$@"
