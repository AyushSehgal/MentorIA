"""Generate the labeled DEMO fixture PDFs (fictional student, fictional course)."""
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

OUT = Path(__file__).resolve().parents[1] / "fixtures" / "demo_docs"

GRADED = [
    [("1", "Caches & Locality", "Which loop order over a row-major 2D array has better spatial locality?",
      "Row-major (inner loop over columns)", "Correct", "2/2", "Good."),
     ("2", "Cache Coherence", "Under MESI, a core holds line X in Shared. Another core issues BusRdX for X. What is the new state?",
      "Stays Shared", "Incorrect", "0/2", "BusRdX invalidates other copies: S -> I.")],
    [("3", "Cache Coherence", "Why does a write to a line in Shared state require a bus transaction?",
      "It doesn't if the line is clean", "Incorrect", "0/2", "Other sharers must be invalidated (BusUpgr/BusRdX)."),
     ("4", "Virtual Memory", "What does the TLB cache?", "Recent virtual-to-physical page translations", "Correct", "2/2", "")],
    [("5", "Synchronization", "Two threads run counter++ 1000 times each without a lock. Can the final value be < 2000?",
      "No, ++ is atomic on x86", "Incorrect", "0/2", "Load/add/store can interleave: a race condition."),
     ("6", "Virtual Memory", "What happens on a page fault for a valid but non-resident page?",
      "OS loads the page from disk and restarts the instruction", "Correct", "2/2", ""),
     ("7", "Processes & Signals", "What does fork() return in the child process?", "The parent's PID", None, "1/2",
      "Partial credit: returns 0 in the child.")],
]

UNGRADED = [
    [("1", "Virtual Memory", "Explain how a two-level page table reduces memory overhead."),
     ("2", "Virtual Memory", "Compute the number of TLB entries needed to cover 2 MB with 4 KB pages.")],
    [("3", "Caches & Locality", "Give an example of temporal locality in a loop.")],
]


def wrap(c, text, x, y, width=88):
    words, line = text.split(), ""
    for w in words:
        if len(line) + len(w) + 1 > width:
            c.drawString(x, y, line)
            y -= 14
            line = w
        else:
            line = (line + " " + w).strip()
    if line:
        c.drawString(x, y, line)
        y -= 14
    return y


def header(c, title, sub, page, total):
    c.setFont("Helvetica-Bold", 13)
    c.drawString(54, 740, title)
    c.setFont("Helvetica", 9)
    c.drawString(54, 726, sub)
    c.drawString(470, 726, f"Page {page} of {total}")
    c.setFillColorRGB(0.75, 0.1, 0.1)
    c.drawString(54, 712, "DEMO DATA - fictional student and course, generated for the NOVA demo.")
    c.setFillColorRGB(0, 0, 0)


def graded():
    c = canvas.Canvas(str(OUT / "systems_quiz3_graded.pdf"), pagesize=letter)
    for i, page in enumerate(GRADED, 1):
        header(c, "Computer Systems - Quiz 3 (Graded)",
               "Course: Computer Systems (demo course)   Student: Alex (demo student)   Date: 2026-10-20   Total: 7/14", i, len(GRADED))
        y = 680
        for q, topic, prompt, ans, res, score, comment in page:
            c.setFont("Helvetica-Bold", 10)
            c.drawString(54, y, f"Q{q}.")
            y -= 14
            c.setFont("Helvetica", 10)
            c.drawString(54, y, f"Topic: {topic}")
            y -= 14
            y = wrap(c, f"Question: {prompt}", 54, y)
            c.drawString(54, y, f"Student answer: {ans}")
            y -= 14
            if res:
                c.drawString(54, y, f"Result: {res}")
                y -= 14
            c.drawString(54, y, f"Score: {score}")
            y -= 14
            if comment:
                y = wrap(c, f"Grader comment: {comment}", 54, y)
            y -= 16
        c.showPage()
    c.save()


def ungraded():
    c = canvas.Canvas(str(OUT / "systems_vm_practice_ungraded.pdf"), pagesize=letter)
    for i, page in enumerate(UNGRADED, 1):
        header(c, "Computer Systems - Virtual Memory Practice Problems",
               "Course: Computer Systems (demo course)   Question sheet only - no answers or grades", i, len(UNGRADED))
        y = 680
        for q, topic, prompt in page:
            c.setFont("Helvetica-Bold", 10)
            c.drawString(54, y, f"Q{q}.")
            y -= 14
            c.setFont("Helvetica", 10)
            c.drawString(54, y, f"Topic: {topic}")
            y -= 14
            y = wrap(c, prompt, 54, y) - 16
        c.showPage()
    c.save()


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    graded()
    ungraded()
    print("wrote", *sorted(p.name for p in OUT.glob("*.pdf")))
