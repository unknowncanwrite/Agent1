"""Adversarial memory tests: persistence, unicode, limits."""
import tempfile
from pathlib import Path

from agent1.memory import Memory


def test_persistence_and_search():
    with tempfile.TemporaryDirectory() as tmp:
        db = str(Path(tmp) / "m.db")
        m = Memory(db)
        m.save_fact("the sky is blue", "nature")
        m.save_fact("user likes Python and Urdu poetry ✓", "prefs")
        m.save_fact("unrelatedxyz", "misc")
        m.close()
        m2 = Memory(db)
        hits = m2.search("python poetry")
        assert any("Urdu" in f for _, f in hits)
        assert m2.search("") != []  # empty -> recent
        assert m2.search("zzz-no-match-here") == []
        m2.save_episode("task T", "did things")
        assert "task T" in (Path(tmp) / "episodes.md").read_text()
        m2.close()


def test_special_chars_and_long():
    with tempfile.TemporaryDirectory() as tmp:
        m = Memory(str(Path(tmp) / "m.db"))
        m.save_fact("quotes '\"; drop table facts; --", "inj';ection")
        m.save_fact("x" * 5000, "long")
        assert m.search("quotes") != []
        assert m.search("xxxxxxxx") != []
        m.close()
