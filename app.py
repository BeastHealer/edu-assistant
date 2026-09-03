"""Streamlit-интерфейс ИИ-куратора EduPath."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import plotly.express as px
import streamlit as st

from config import settings
from edu_curator.analytics.reports import (
    build_markdown_report,
    explode_topics,
    frequent_questions,
    load_queries,
)
from edu_curator.lms.stub import LMSStub
from edu_curator.models import CuratorRequest, StudentLevel
from edu_curator.rag.indexer import index_knowledge
from edu_curator.rag.loader import load_knowledge_documents

st.set_page_config(
    page_title="EduPath · ИИ-куратор",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
.stApp { background: radial-gradient(1200px 500px at 10% -10%, #1b2744 0%, #0f1219 45%); }
.hero {
    padding: 1.2rem 1.4rem; border: 1px solid #2a3550; border-radius: 18px;
    background: linear-gradient(135deg, rgba(76,111,255,.18), rgba(16,24,40,.65));
    margin-bottom: 1rem;
}
.hero h1 { margin: 0 0 .35rem 0; font-size: 1.7rem; }
.hero p { margin: 0; color: #b7c0d3; }
.badge {
    display: inline-block; padding: .15rem .55rem; border-radius: 999px;
    background: #243056; color: #c9d4ff; font-size: .78rem; margin-right: .35rem;
}
.source-card {
    padding: .75rem 1rem; border-radius: 12px; border: 1px solid #2a3550;
    background: #151b2b; margin-bottom: .5rem; font-size: .9rem;
}
.metric-help { color: #8b95ab; font-size: .8rem; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def ensure_index() -> dict:
    meta_path = settings.chroma_dir / "index_meta.json"
    tfidf_path = settings.chroma_dir / "tfidf.pkl"
    chroma_path = settings.chroma_dir / "chroma_store"
    if meta_path.exists() or tfidf_path.exists() or chroma_path.exists():
        if meta_path.exists():
            return json.loads(meta_path.read_text(encoding="utf-8"))
        return {"store": "existing"}
    with st.spinner("Индексирую базу знаний…"):
        return index_knowledge()


@st.cache_resource(show_spinner=False)
def get_cached_agent():
    from edu_curator.curator.agent import CuratorAgent

    return CuratorAgent()


@st.cache_data
def knowledge_catalog():
    docs = load_knowledge_documents()
    rows = []
    for doc in docs:
        rows.append({**doc.metadata, "chars": len(doc.page_content)})
    return pd.DataFrame(rows)


def render_hero() -> None:
    st.markdown(
        f"""
        <div class="hero">
          <div class="badge">демо без реальных ПДн</div>
          <div class="badge">{settings.platform_name}</div>
          <h1>ИИ-куратор {settings.curator_name}</h1>
          <p>Наставник курса «{settings.course_title}»: дедлайны, сложность материала,
          рекомендации и помощь по заданиям — со ссылкой на источник.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def sidebar_controls(agent) -> dict:
    st.sidebar.header("Профиль студента")
    lms = LMSStub()
    people = lms.get_students()["students"]
    labels = [f"{p['display_name']} · {p['student_id']}" for p in people]
    picked = st.sidebar.selectbox("Учебный профиль", labels)
    person = people[labels.index(picked)]

    level_label = st.sidebar.radio(
        "Уровень объяснений",
        ["beginner", "advanced"],
        index=0 if person["track_level"] == "beginner" else 1,
        format_func=lambda x: "Начинающий" if x == "beginner" else "Продвинутый",
    )

    st.sidebar.header("Фильтры RAG")
    modules = ["Все"] + agent.retriever.unique_values("module")
    types = ["Все"] + agent.retriever.unique_values("resource_type")
    topics = ["Все"] + agent.retriever.unique_values("topic")
    module = st.sidebar.selectbox("Модуль", modules)
    resource_type = st.sidebar.selectbox("Тип ресурса", types)
    topic = st.sidebar.selectbox("Тема", topics)

    st.sidebar.header("Статус")
    st.sidebar.write(f"LLM: `{agent.llm_backend}`")
    st.sidebar.write(f"Поиск: `{agent.retriever.backend}`")
    st.sidebar.caption("Без ключа GigaChat работает офлайн-синтез по найденным фрагментам.")
    return {
        "person": person,
        "level": StudentLevel(level_label),
        "module": None if module == "Все" else module,
        "resource_type": None if resource_type == "Все" else resource_type,
        "topic": None if topic == "Все" else topic,
    }


def page_chat(agent, ctx: dict) -> None:
    render_hero()
    if "messages" not in st.session_state:
        st.session_state.messages = []

    examples = [
        "Когда дедлайн первого домашнего задания?",
        "Я ничего не понимаю в корреляции, это слишком сложно",
        "Что почитать дополнительно, если Python для меня новый?",
        "Напиши готовый код топ-5 городов для ДЗ-1",
        "Поставь мне зачёт и перенеси дедлайн проекта",
        "Что такое переобучение и как его заметить?",
    ]
    cols = st.columns(3)
    for i, text in enumerate(examples):
        if cols[i % 3].button(text, use_container_width=True):
            st.session_state.pending_question = text

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("meta"):
                st.caption(message["meta"])

    prompt = st.chat_input("Спросите куратора по курсу, дедлайнам или материалам…")
    question = st.session_state.pop("pending_question", None) or prompt
    if not question:
        return

    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    history = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.messages[:-1]
        if m["role"] in {"user", "assistant"}
    ]
    request = CuratorRequest(
        question=question,
        level=ctx["level"],
        student_id=ctx["person"]["student_id"],
        student_name=ctx["person"]["display_name"],
        module_filter=ctx["module"],
        resource_type_filter=ctx["resource_type"],
        topic_filter=ctx["topic"],
        chat_history=history,
    )
    with st.chat_message("assistant"):
        with st.spinner("Куратор смотрит материалы курса…"):
            response = agent.ask(request)
        st.markdown(response.answer)
        meta = (
            f"Сценарий: `{response.scenario.value}` · уверенность: `{response.confidence}` · "
            f"модель: `{response.llm_backend}`"
        )
        if response.blocked:
            meta += f" · сработал гардрейл (`{response.block_reason}`)"
        st.caption(meta)
        if response.sources:
            with st.expander("Найденные фрагменты RAG"):
                for chunk in response.sources:
                    st.markdown(
                        f"<div class='source-card'><b>{chunk.doc_id}</b> · {chunk.module} · "
                        f"{chunk.resource_type}<br>{chunk.topic}<br>"
                        f"<span class='metric-help'>score={chunk.score:.3f} · {chunk.source}</span></div>",
                        unsafe_allow_html=True,
                    )
    st.session_state.messages.append(
        {"role": "assistant", "content": response.answer, "meta": meta}
    )


def page_analytics() -> None:
    st.title("Аналитика запросов")
    st.caption("Учебные логи. Профили вымышленные. Живые запросы из чата попадают сюда же.")
    df = load_queries()
    if df.empty:
        st.warning("Лог пуст. Запустите `python scripts/seed_analytics.py` или позадавайте вопросы в чате.")
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Запросов", len(df))
    c2.metric("Уникальных формулировок", df["question"].nunique())
    c3.metric("Сценариев", df["scenario"].nunique())
    c4.metric("Гардрейлы", int(df["blocked"].sum()) if "blocked" in df else 0)

    left, right = st.columns(2)
    scenario_df = df["scenario"].value_counts().reset_index()
    scenario_df.columns = ["scenario", "count"]
    fig1 = px.bar(scenario_df, x="scenario", y="count", title="Сценарии обращений")
    fig1.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    left.plotly_chart(fig1, use_container_width=True)

    if df["created_at"].notna().any():
        daily = df.dropna(subset=["created_at"]).copy()
        daily["day"] = daily["created_at"].dt.date
        ts = daily.groupby("day").size().reset_index(name="count")
        fig2 = px.line(ts, x="day", y="count", markers=True, title="Динамика запросов")
        fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        right.plotly_chart(fig2, use_container_width=True)

    topics = explode_topics(df)
    left, right = st.columns(2)
    if not topics.empty:
        fig3 = px.bar(topics.head(12), x="count", y="topic", orientation="h", title="Частые темы")
        fig3.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", yaxis={"categoryorder": "total ascending"})
        left.plotly_chart(fig3, use_container_width=True)
    level_df = df["level"].value_counts().reset_index()
    level_df.columns = ["level", "count"]
    fig4 = px.pie(level_df, names="level", values="count", title="Уровни")
    fig4.update_layout(paper_bgcolor="rgba(0,0,0,0)")
    right.plotly_chart(fig4, use_container_width=True)

    st.subheader("Повторяющиеся вопросы — сигнал для улучшения контента")
    st.dataframe(frequent_questions(df, 12), use_container_width=True, hide_index=True)

    st.subheader("Текстовый отчёт")
    report = build_markdown_report(df)
    st.markdown(report)
    st.download_button("Скачать отчёт Markdown", report, file_name="curator_analytics_report.md")


def page_knowledge() -> None:
    st.title("База знаний")
    catalog = knowledge_catalog()
    st.caption(f"{len(catalog)} документов · лекции, методички, FAQ, доп. ресурсы")
    st.dataframe(
        catalog[
            ["doc_id", "module", "resource_type", "topic", "difficulty", "source", "chars"]
        ],
        use_container_width=True,
        hide_index=True,
    )
    docs = load_knowledge_documents()
    titles = [f"{d.metadata['doc_id']} — {d.metadata.get('title', '')}" for d in docs]
    choice = st.selectbox("Просмотр документа", titles)
    doc = docs[titles.index(choice)]
    st.markdown(doc.page_content)


def page_lms() -> None:
    st.title("Заглушка LMS")
    st.caption("Имитация интеграции: JSON/CSV выгрузки расписания и заданий. Данные вымышленные.")
    lms = LMSStub()
    tab1, tab2, tab3, tab4 = st.tabs(["Расписание", "Задания", "Модули", "Выгрузки API"])
    with tab1:
        st.dataframe(pd.DataFrame(lms.get_schedule()["events"]), use_container_width=True, hide_index=True)
    with tab2:
        st.dataframe(pd.DataFrame(lms.get_assignments()), use_container_width=True, hide_index=True)
    with tab3:
        st.dataframe(pd.DataFrame(lms.get_modules()["modules"]), use_container_width=True, hide_index=True)
        st.subheader("Учебные профили (не ПДн)")
        st.dataframe(pd.DataFrame(lms.get_students()["students"]), use_container_width=True, hide_index=True)
    with tab4:
        st.code(
            "GET /api/lms/schedule → schedule.json\n"
            "GET /api/lms/assignments → assignments.csv\n"
            "GET /api/lms/modules → modules.json\n"
            "GET /api/lms/export/schedule.csv\n"
            "GET /api/lms/export/assignments.json",
            language="text",
        )
        st.download_button("schedule.csv", lms.export_schedule_csv(), file_name="schedule.csv")
        st.download_button("assignments.json", lms.export_assignments_json(), file_name="assignments.json")
        st.json({"sample_endpoint": "/api/lms/schedule", "payload": lms.get_schedule()})


def page_docs() -> None:
    st.title("Документация")
    docs_dir = ROOT / "docs"
    files = sorted(docs_dir.glob("*.md"))
    names = [f.stem for f in files]
    if not names:
        st.info("Папка docs пока пуста.")
        return
    name = st.selectbox("Документ", names)
    path = docs_dir / f"{name}.md"
    st.markdown(path.read_text(encoding="utf-8"))


def main() -> None:
    meta = ensure_index()
    agent = get_cached_agent()
    page = st.sidebar.radio(
        "Разделы",
        ["Чат с куратором", "Аналитика", "База знаний", "LMS", "Документация"],
    )
    ctx = sidebar_controls(agent) if page == "Чат с куратором" else {}
    st.sidebar.caption("Индекс: " + json.dumps(meta, ensure_ascii=False))

    if page == "Чат с куратором":
        page_chat(agent, ctx)
    elif page == "Аналитика":
        page_analytics()
    elif page == "База знаний":
        page_knowledge()
    elif page == "LMS":
        page_lms()
    else:
        page_docs()


if __name__ == "__main__":
    main()
