from __future__ import annotations

from pathlib import Path

from site_scraper.config import GENERATED_ROOT
from site_scraper.models import SiteConfig


def generate_site(config: SiteConfig, latest_run: Path | None = None) -> Path:
    out = GENERATED_ROOT / config.name
    backend = out / "backend"
    frontend = out / "frontend"
    backend.mkdir(parents=True, exist_ok=True)
    frontend.mkdir(parents=True, exist_ok=True)
    (out / "pyproject.toml").write_text(f'''[project]
name = "{config.name}-generated-site"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["duckdb>=1.1.3", "fastapi>=0.115.6", "reflex>=0.6.6", "uvicorn>=0.32.1", "pyarrow>=18.1.0"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
''')
    (backend / "main.py").write_text('''from pathlib import Path

import duckdb
from fastapi import FastAPI

app = FastAPI(title="Generated scraped-data API")
DATA_ROOT = Path(__file__).resolve().parents[1] / "data"
DUCKDB_PATH = DATA_ROOT / "catalog.duckdb"

@app.get("/health")
def health():
    return {"ok": True, "duckdb_exists": DUCKDB_PATH.exists()}

@app.get("/tables")
def tables():
    if not DUCKDB_PATH.exists():
        return []
    con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
    try:
        rows = con.execute("select table_name from information_schema.tables where table_schema = 'scraped'").fetchall()
        return [row[0] for row in rows]
    finally:
        con.close()
''')
    (frontend / "app.py").write_text(f'''import reflex as rx


def index() -> rx.Component:
    return rx.container(
        rx.heading("{config.name}", size="7"),
        rx.text("Generated from scraped DuckDB/Parquet data."),
        rx.link("API health", href="http://localhost:8000/health"),
        padding="2rem",
    )

app = rx.App()
app.add_page(index)
''')
    (out / "Dockerfile.backend").write_text('''FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir duckdb fastapi uvicorn pyarrow
COPY backend /app/backend
COPY data /app/data
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
''')
    (out / "Dockerfile.frontend").write_text('''FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir reflex
COPY frontend /app
CMD ["reflex", "run", "--env", "prod", "--backend-only", "--backend-port", "3000"]
''')
    (out / "docker-compose.yml").write_text('''services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    ports:
      - "8000:8000"
  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend
''')
    (out / "README.md").write_text("# Generated site\n\n```bash\nuv sync\ndocker compose up --build\n```\n")
    data = out / "data"
    data.mkdir(exist_ok=True)
    if latest_run and (latest_run / "catalog.duckdb").exists():
        (data / "catalog.duckdb").write_bytes((latest_run / "catalog.duckdb").read_bytes())
    return out
