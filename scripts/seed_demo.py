"""Reset the local DB to the deterministic demo scenario. Usage: backend/.venv/bin/python scripts/seed_demo.py [--with-quiz]"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.config import FIXTURES_DIR  # noqa: E402
from app.services.document_ingest import ingest_pdf  # noqa: E402
from app.services.seed import reset  # noqa: E402

reset()
if "--with-quiz" in sys.argv:
    p = FIXTURES_DIR / "demo_docs" / "systems_quiz3_graded.pdf"
    d = ingest_pdf(p.read_bytes(), p.name, "demo_student", None, is_fixture=True)
    print(f"ingested {d.title}: {d.observations_created} accepted, {d.pending_review} pending review")
print("demo reset complete")
