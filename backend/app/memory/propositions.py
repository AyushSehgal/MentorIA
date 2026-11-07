"""Semantic propositions (goals, interests, preferences): extraction from student-authored text + merging.

Only text the student wrote (chat, emails they sent, documents they mark as their own) is mined. A statement that
matches an existing active proposition of the same category is merged into it as additional evidence, so the same goal
said in a statement, an email and chat becomes one goal "stated in 3 sources" instead of three duplicates.
"""
from __future__ import annotations

import re
from typing import Optional

from ..schemas import SemanticProposition
from . import store

GOAL = re.compile(r"\b(?:my (?:career )?goal is(?: to)?|i want to|i'd like to|i would like to|i hope to|i plan to|i want an?|i'd love to)\s+([^.;!?\n]+)", re.I)
INTEREST = re.compile(r"\bi(?:'m| am)\s+(?:(?:really|very|especially|most|also|deeply)\s+)*(?:interested in|excited about|passionate about)\s+([^.;!?\n]+)", re.I)
PREFER = re.compile(r"\bi prefer\s+([^.;!?\n]+)", re.I)
QUESTIONISH = re.compile(r"\b(know|what|which|how|should)\b|\?", re.I)
STOP = set("""a an the to of in on at for and or with that which who is are be been being i me my we our you your it its this
these those as by from into about at would like want hope plan love job work after graduation graduate goal career
make makes making build builds building do does doing really very also ideally eventually one some such than then""".split())


def _sentence(text: str, start: int, end: int) -> str:
    s = max(text.rfind(".", 0, start), text.rfind("\n", 0, start), text.rfind("!", 0, start), text.rfind("?", 0, start)) + 1
    e_candidates = [i for i in (text.find(".", end), text.find("\n", end), text.find("!", end)) if i != -1]
    e = min(e_candidates) + 1 if e_candidates else len(text)
    return re.sub(r"\s+", " ", text[s:e]).strip()


def extract(text: str) -> list[tuple[str, str]]:
    """[(category, sentence)] for explicit first-person goals/interests/preferences in student-authored text."""
    out: list[tuple[str, str]] = []
    for rx, kind in ((GOAL, "goal"), (INTEREST, "interest"), (PREFER, "preference")):
        for m in rx.finditer(text):
            clause = m.group(1).strip()
            if kind == "goal" and QUESTIONISH.search(clause):
                continue
            if len(clause) < 6:
                continue
            sent = _sentence(text, m.start(), m.end())
            if (kind, sent) not in out:
                out.append((kind, sent))
    return out


def _tokens(statement: str) -> set[str]:
    words = re.findall(r"[a-z][a-z\-]+", statement.lower())
    out = set()
    for w in words:
        for part in w.split("-"):
            if part.endswith("ing") and len(part) > 5:
                part = part[:-3]
            elif part.endswith("s") and len(part) > 4:
                part = part[:-1]
            if len(part) > 2 and part not in STOP:
                out.add(part)
    return out


def similar(a: str, b: str) -> bool:
    ta, tb = _tokens(a), _tokens(b)
    if len(ta) < 2 or len(tb) < 2:
        return False
    shared = len(ta & tb)
    return shared >= 3 and shared / min(len(ta), len(tb)) >= 0.5


def find_match(student_id: str, category: str, statement: str) -> Optional[SemanticProposition]:
    for p in store.list_propositions(student_id):
        if p.category == category and p.status not in ("expired",) and similar(p.statement, statement):
            return p
    return None
