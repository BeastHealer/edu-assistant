# RAG-схема базы знаний

## Источники

| Тип (`resource_type`) | Папка | Зачем в индексе |
| --- | --- | --- |
| `lecture` | `data/knowledge/lectures/` | концепции, определения |
| `methodic` | `data/knowledge/methodics/` | как учиться, брифы ДЗ и проекта |
| `faq` | `data/knowledge/faq/` | организация, техника, трудности |
| `extra` | `data/knowledge/extras/` | рекомендации ресурсов |

Канонические **даты сдачи** дублируются в LMS (`data/lms/assignments.csv`). В промпт они подаются отдельным блоком, чтобы модель не путала устаревший чанк лекции с текущим дедлайном.

## Метаданные документа (YAML frontmatter)

```yaml
doc_id: LEC-M2-01
module: M2
module_title: Python и pandas
topic: Основы Python, Jupyter и работа с таблицами
resource_type: lecture
difficulty: beginner
week: 2
```

Фильтры поиска в UI и в retriever: `module`, `resource_type`, `topic`.

## Нарезка

- Сплиттер: RecursiveCharacterTextSplitter.
- `chunk_size=700`, `overlap=120`, приоритет разделителей `##` / `###`.
- `chunk_id = {doc_id}-{n}`.

## Эмбеддинги (auto)

1. GigaChat Embeddings — если есть ключ.
2. HuggingFace `paraphrase-multilingual-MiniLM-L12-v2` — если установлен `sentence-transformers`.
3. Локальный TF-IDF (char_wb 1–2) — всегда, без скачивания моделей.

Индекс: Chroma в `data/chroma/chroma_store` либо pickle TF-IDF `data/chroma/tfidf.pkl`.

## Запрос

```
search_query = вопрос + retrieval_hint(сценарий)
k = 5
```

Подсказка сценария подтягивает нужный тип (для дедлайнов — FAQ/организация, для ДЗ — методичка).

Если пользовательский фильтр дал 0 чанков, выполняется повтор без фильтра.

## Оценка релевантности в демо

- Ручная: вопросы из few-shot и кнопки-примеры в Streamlit.
- Автотесты: дедлайн HW1 находится, источники присутствуют.
- Для продакшена: набор gold-вопросов и Recall@5 по `doc_id`.

## Схема данных чанка (логика)

```
RetrievedChunk:
  text, source, doc_id, module, topic, resource_type, difficulty, score
```

В лог аналитики пишутся не сырые ПДн, а `student_id` учебных профилей, сценарий, список тем и `doc_id` источников.
