from edu_curator.lms.stub import LMSStub
from edu_curator.rag.loader import load_knowledge_documents


def test_lms_assignments_have_deadlines():
    rows = LMSStub().get_assignments()
    assert len(rows) >= 4
    assert all(row["deadline"] for row in rows)


def test_lms_exports():
    lms = LMSStub()
    csv_data = lms.export_schedule_csv()
    assert "webinar" in csv_data
    payload = lms.export_assignments_json()
    assert "HW1" in payload


def test_knowledge_frontmatter():
    docs = load_knowledge_documents()
    assert len(docs) >= 10
    ids = {d.metadata["doc_id"] for d in docs}
    assert "LEC-M2-01" in ids
    assert "FAQ-ORG-01" in ids
    types = {d.metadata["resource_type"] for d in docs}
    assert {"lecture", "methodic", "faq", "extra"} <= types
