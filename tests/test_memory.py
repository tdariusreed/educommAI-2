from memory.profile_store import ProfileStore
from memory.vector_store import KnowledgeStore


def test_profile_roundtrip_isolation_delete(tmp_path):
    s = ProfileStore(tmp_path / "p.db")
    s.set_fields("a", {"grade": 11, "interests": ["math"], "location": "Atlanta"})
    p = s.load("a")
    assert p.grade == 11 and p.interests == ["math"] and s.load("b").grade is None
    s.delete_field("a", "location")
    assert s.load("a").location == ""
    s.delete_all("a")
    assert s.fields("a") == []


def test_interests_merge_other_fields_replace_invalid_dropped(tmp_path):
    s = ProfileStore(tmp_path / "p.db")
    s.set_fields("u", {"interests": ["math"], "grade": 9})
    s.set_fields("u", {"interests": ["Art", "MATH"], "grade": 10, "grade2": 1})
    assert s.load("u").interests == ["math", "Art"] and s.load("u").grade == 10
    s.set_fields("u", {"grade": 3})
    assert s.load("u").grade == 10
    s.set_fields("u", {"interests": ["music"]}, replace=True)
    assert s.load("u").interests == ["music"]


def test_profile_text_is_scrubbed_before_storing(tmp_path):
    s = ProfileStore(tmp_path / "p.db")
    s.set_fields("u", {"location": "123 Peachtree Street", "goal": "call me 404-555-1234", "interests": ["a@b.com"]})
    stored = str(s.fields("u"))
    assert "Peachtree" not in stored and "404-555-1234" not in stored and "a@b.com" not in stored


def test_knowledge_store(tmp_path):
    (tmp_path / "aid.md").write_text("---\nsource: https://studentaid.gov/x\ntitle: Aid\n---\nFederal student aid and the FAFSA form help pay for college.")
    (tmp_path / "other.md").write_text("Bees make honey in hives.")
    (tmp_path / "README.md").write_text("ignore me")
    assert KnowledgeStore.has_documents(tmp_path) and not KnowledgeStore.has_documents(tmp_path / "missing")
    k = KnowledgeStore(tmp_path)
    assert len(k) == 2 and k.search("how do I pay for college with FAFSA")[0]["url"] == "https://studentaid.gov/x"
    assert k.search("zzzz") == []
