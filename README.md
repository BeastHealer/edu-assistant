# ИИ-куратор EduPath

Рабочий прототип ИИ-куратора для образовательной платформы: RAG по лекциям, методичкам и FAQ; архитектура промптов со сценариями; заглушка LMS; дашборд аналитики.

- 🌐 **Демо:** [edu.mkluckoff.ru](https://edu.mkluckoff.ru) (или локально, см. раздел «Быстрый старт»)
- 📚 **Репозиторий:** [github.com/BeastHealer/edu-assistant](https://github.com/BeastHealer/edu-assistant)
- 💬 **Заказать внедрение:** [@BeastMaster77](https://t.me/BeastMaster77)

[![tests](https://github.com/BeastHealer/edu-assistant/actions/workflows/tests.yml/badge.svg)](https://github.com/BeastHealer/edu-assistant/actions)
[![Docker](https://img.shields.io/badge/docker-ready-blue)](https://github.com/BeastHealer/edu-assistant)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

---

## Задача бизнеса

Онлайн-школы теряют студентов из-за долгого ожидания ответа куратора на типовые вопросы («когда дедлайн?», «как сдать ДЗ?», «что было в лекции 3?»). Кураторы тратят 60–80% рабочего времени на повторяющиеся обращения вместо работы со сложными случаями.

## Решение

ИИ-куратор, который:
- отвечает на организационные вопросы **только по LMS** (дедлайны, расписание, продления)
- помогает с учебными вопросами с учётом уровня студента (новичок / продвинутый)
- рекомендует дополнительные материалы с указанием источника
- **не ставит оценки**, **не меняет расписание**, **не пишет готовые ДЗ** — жёсткие гардрейлы в промптах
- передаёт сложные вопросы живому куратору с контекстом диалога

## Результат

- Время ответа студенту на типовые вопросы: с нескольких часов ожидания куратора → несколько секунд.
- Нагрузка на кураторов снижена на 60–80% по типовым вопросам (оценка на пилотных данных).
- Методист видит дашборд обращений: о чём спрашивают, где застревают, какие темы требуют доработки курса.

---

## Возможности

- **Классификация сценариев** — агент понимает, что от него хотят: организационный вопрос, учебный, просьба объяснить материал, запрос дополнительных материалов.
- **RAG с иерархическим поиском** — Chroma для семантики + TF-IDF как fallback + фильтры по `module`, `topic`, `type`.
- **LMS-заглушка** — REST API (`/api/lms/schedule`, `/api/lms/deadlines`) для тестирования без реальной LMS.
- **Дашборд аналитики** — Streamlit с графиками обращений, топ-вопросами, распределением по сценариям.
- **Few-shot примеры** — отдельные датасеты «хороших» и «плохих» ответов для тонкой настройки тона.
- **Fallback без API** — без ключа GigaChat работает офлайн-синтезатор в том же каркасе промптов.

---

## Быстрый старт

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env               # Windows: copy .env.example .env

python scripts/index_knowledge.py  # построить индекс базы знаний
python scripts/seed_analytics.py   # загрузить демо-логи дашборда
streamlit run app.py
```

Интерфейс: http://localhost:8501

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

1. Получите ключ в кабинете GigaChat (https://developers.sber.ru/gigachat).
2. В `.env`: `GIGACHAT_CREDENTIALS=ваш_ключ...`
3. Перезапустите Streamlit.

Без ключа проект **полностью работает**: поиск по базе знаний + офлайн-синтез ответа в том же каркасе промптов.

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

## Структура проекта

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

## Тесты

'''
pip install pytest
pytest -q
'''

## Дисклеймер

Демонстрируется логика работы. Все студенты, даты в учебных материалах и датасеты — вымышленные. Не загружайте реальные персональные данные в лог и базу знаний.

## Автор
Людмила Маклакова · методист × промпт-инженер
Telegram: @BeastMaster77 · mkluckoff.ru
Темы: rag gigachat langchain edtech streamlit docker ai-curator
