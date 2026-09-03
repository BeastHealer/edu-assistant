"""Переиндексация базы знаний.

Запуск из корня проекта:
    python scripts/index_knowledge.py
    python scripts/index_knowledge.py --force
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from edu_curator.rag.indexer import index_knowledge  # noqa: E402


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Индексация базы знаний EduPath")
    parser.add_argument("--force", action="store_true", help="Пересоздать индекс")
    args = parser.parse_args()
    meta = index_knowledge(force=args.force)
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
