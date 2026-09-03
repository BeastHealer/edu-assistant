"""Точка входа контейнера: индекс → демо-логи → Streamlit или LMS API."""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _run(args: list[str]) -> None:
    subprocess.check_call(args)


def ensure_index() -> None:
    persist = ROOT / "data" / "chroma"
    persist.mkdir(parents=True, exist_ok=True)
    ready = (persist / "index_meta.json").exists() or (persist / "tfidf.pkl").exists()
    if ready and os.environ.get("REINDEX_ON_START", "").lower() not in {"1", "true", "yes"}:
        print("RAG-индекс уже есть, пропускаю индексацию", flush=True)
        return
    print("Индексирую базу знаний…", flush=True)
    _run([sys.executable, "scripts/index_knowledge.py"])


def ensure_analytics_seed() -> None:
    db_path = ROOT / "data" / "analytics" / "queries.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if os.environ.get("SEED_ANALYTICS", "1").lower() in {"0", "false", "no"}:
        return
    if db_path.exists():
        try:
            with sqlite3.connect(db_path) as conn:
                count = conn.execute("SELECT COUNT(*) FROM queries").fetchone()[0]
            if count:
                print(f"Аналитика уже содержит {count} записей, seed пропускаю", flush=True)
                return
        except sqlite3.Error:
            pass
    print("Заполняю учебные логи аналитики…", flush=True)
    _run([sys.executable, "scripts/seed_analytics.py"])


def run_streamlit() -> None:
    port = os.environ.get("STREAMLIT_SERVER_PORT", "8501")
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "app.py",
        "--server.address=0.0.0.0",
        f"--server.port={port}",
        "--server.headless=true",
    ]
    if os.environ.get("STREAMLIT_BEHIND_PROXY", "").lower() in {"1", "true", "yes"}:
        cmd += [
            "--server.enableCORS=false",
            "--server.enableXsrfProtection=false",
            "--server.enableWebsocketCompression=false",
        ]
    os.execvp(sys.executable, cmd)


def run_lms() -> None:
    os.execvp(sys.executable, [sys.executable, "scripts/lms_api.py"])


def main() -> None:
    mode = (sys.argv[1] if len(sys.argv) > 1 else "curator").strip().lower()
    if mode in {"lms", "lms-api"}:
        run_lms()
        return
    ensure_index()
    ensure_analytics_seed()
    run_streamlit()


if __name__ == "__main__":
    main()
