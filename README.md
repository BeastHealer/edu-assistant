# ИИ-куратор EduPath

Рабочий прототип ИИ-куратора для образовательной платформы: RAG по лекциям/методичкам/FAQ, архитектура промптов со сценариями, заглушка LMS и дашборд аналитики.

- Демо: http://edu.5.35.82.97.sslip.io/
- Репозиторий: https://github.com/BeastHealer/edu-assistant

Курс в демо вымышленный: **«Data Science: от нуля до первого проекта»**. Персональные данные не используются — только учебные профили.

## Что умеет куратор

- Отвечает на организационные вопросы (дедлайны, вебинары, продления) **только по LMS**.
- Помогает с учебными вопросами и сложностью материала (новичок / продвинутый).
- Рекомендует дополнительные ресурсы с учётом уровня.
- **Не ставит оценки**, **не меняет расписание**, **не пишет готовые ДЗ**, всегда указывает источник.

## Быстрый старт

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

pip install -r requirements.txt
copy .env.example .env          # Windows; на Unix: cp .env.example .env

python scripts/index_knowledge.py
python scripts/seed_analytics.py
streamlit run app.py
```

Интерфейс: чат, аналитика, база знаний, LMS-выгрузки, документация.

## Docker

Нужны Docker Engine и Docker Compose v2.

```bash
# ключи GigaChat подхватятся из локального .env (файл не копируется в образ)
copy .env.example .env          # если ещё нет

docker compose up --build
```

- UI куратора: http://localhost:8501
- заглушка LMS API: http://localhost:8765/health

Прод на VPS (nginx, не открывать 8501 наружу):

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Публичный адрес текущего стенда: http://edu.5.35.82.97.sslip.io/

Индекс RAG и база аналитики хранятся в томах `curator_index` и `curator_analytics` — повторный запуск не перетирает живые логи чата.

Только интерфейс, без LMS API:

```bash
docker compose up --build curator
```

Переиндексация при старте: `REINDEX_ON_START=1 docker compose up`

Остановка: `docker compose down`. Тома сохранить. Удалить вместе с данными: `docker compose down -v`.

Опционально — имитация REST LMS (локально, без Docker):

```bash
python scripts/lms_api.py
# http://127.0.0.1:8765/api/lms/schedule
```

Тесты:

```bash
pip install pytest
pytest -q
```

## GigaChat

1. Ключ в [кабинете GigaChat](https://developers.sber.ru/gigachat).
2. В `.env`: `GIGACHAT_CREDENTIALS=...`
3. Перезапустите Streamlit.

Без ключа проект **полностью работает**: поиск по базе знаний + офлайн-синтез ответа в том же каркасе промптов (роль, сценарий, уровень, источники, гардрейлы).

Опционально: `OPENAI_API_KEY` и `OPENAI_BASE_URL` для OpenAI-совместимого API.

## Архитектура

```
студент → Streamlit
           → классификатор сценария
           → RAG (Chroma / локальный TF-IDF) + фильтры module/topic/type
           → факты LMS (расписание, дедлайны)
           → системный промпт (роль + ограничения + уровень + few-shot)
           → GigaChat | fallback-синтезатор
           → гардрейлы
           → лог SQLite → дашборд
```

Подробности: `docs/architecture.md`, `docs/prompt-architecture.md`, `docs/rag-schema.md`.

Тексты рассчитаны на перенос в Notion / Google Docs (заголовки, списки, таблицы).

## Структура

```
app.py                      Streamlit UI
config.py                   настройки (.env)
edu_curator/                агент, RAG, LLM, LMS, аналитика
data/knowledge/             лекции, методички, FAQ
data/lms/                   JSON/CSV заглушка LMS
data/few_shot/              корректные и некорректные ответы
scripts/index_knowledge.py  переиндексация
scripts/seed_analytics.py   демо-логи дашборда
notebooks/curator_demo.ipynb
docs/                       архитектура, RAG, промпты, регламент обновления
```

## Дисклеймер

Демонстрируется логика работы. Все студенты, даты в учебных материалах и датасеты — вымышленные. Не загружайте реальные персональные данные в лог и базу знаний.
