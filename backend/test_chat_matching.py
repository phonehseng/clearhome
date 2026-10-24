"""Chat grounding: senior-only homes stay out unless asked, and short names in answers still get their cards."""
from advisor import _pick, cards_for
from catalog import load_catalog, senior_only

rows = load_catalog()

family = _pick(rows, "2 bedroom in Fairfax for a family of 4 making 50k")
assert family and not any(senior_only(r) for r in family), "senior-only homes offered to a family"
assert not any(senior_only(r) for r in _pick(rows, "apartments in fairfax at 60% AMI")), "60% AMI is not an age"
assert any(senior_only(r) for r in _pick(rows, "senior apartments in Fairfax")), "seniors should still see senior homes"

names = [c["name"] for c in cards_for("Call **Arlington DHS** at 703-228-1010. **PathForward** has a Homeless Services Center.")]
assert any("Arlington County DHS" in n for n in names), names
assert any("Path Forward" in n for n in names), names
assert [c["name"] for c in cards_for("**Indigo at McLean Station** and **Exo**")] == ["Indigo at McLean Station", "Exo"]

print("chat matching tests passed")
