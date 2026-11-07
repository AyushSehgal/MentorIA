"""Parse MentorIA "source pack" markdown files (e.g. fixtures/synthetic_world.md, demo_assets/*.md).

A pack can contain any subset of these sections:
  ## Courses / ## Concepts / ## Concept relations     -> markdown tables
  ## Student  (- id:, - name:, ### Completed courses table, ### Self-reports table)
  ## Canvas assignments / ## Calendar events           -> markdown tables
  ## Gmail messages / ## Piazza posts                  -> one ### block per item: "- key: value" fields, blank line, body
Packs are imported on demand (Add data page); nothing is loaded automatically.
"""
from __future__ import annotations

import re
from datetime import datetime
from dataclasses import dataclass, field
from typing import Any


class SyntheticDataError(ValueError):
    pass


@dataclass
class _Block:
    title: str
    lines: list[str] = field(default_factory=list)
    subs: list["_Block"] = field(default_factory=list)


_FIELD = re.compile(r"^\s*[-*]\s*([A-Za-z_ ]+?)\s*:\s*(.*)$")


def _blocks(text: str) -> dict[str, _Block]:
    sections: dict[str, _Block] = {}
    h2: _Block | None = None
    target: _Block | None = None
    in_code = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
        if not in_code and line.startswith("## "):
            h2 = _Block(line[3:].strip())
            sections[h2.title.lower()] = h2
            target = h2
        elif not in_code and line.startswith("### ") and h2 is not None:
            target = _Block(line[4:].strip())
            h2.subs.append(target)
        elif target is not None:
            target.lines.append(line)
    return sections


def _table(lines: list[str], where: str, required: list[str]) -> list[dict[str, str]]:
    rows = [ln.strip() for ln in lines if ln.strip().startswith("|")]
    if not rows:
        raise SyntheticDataError(f"{where}: no table found")
    split = lambda r: [c.strip() for c in r.strip().strip("|").split("|")]  # noqa: E731
    header = [h.lower() for h in split(rows[0])]
    missing = [c for c in required if c not in header]
    if missing:
        raise SyntheticDataError(f"{where}: table is missing column(s) {', '.join(missing)}")
    out = []
    for i, r in enumerate(rows[1:], start=1):
        cells = split(r)
        if all(set(c) <= set("-: ") for c in cells):
            continue  # separator row
        cells += [""] * (len(header) - len(cells))
        out.append(dict(zip(header, cells)) | {"_row": str(i)})
    return out


def _fields_and_body(lines: list[str]) -> tuple[dict[str, str], str]:
    fields: dict[str, str] = {}
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    while i < len(lines) and (m := _FIELD.match(lines[i])):
        fields[m.group(1).strip().lower().replace(" ", "_")] = m.group(2).strip()
        i += 1
    body = "\n".join(lines[i:]).strip()
    body = re.sub(r"\n-{3,}\s*$", "", body).strip()
    return fields, body


_REL = re.compile(r"^d[+-]\d+\s+\d{1,2}:\d{2}$")
_WHEN = re.compile(r"\{when:([^}]+)\}")


def _time(spec: str, where: str, required: bool = True) -> str:
    spec = (spec or "").strip()
    if not spec:
        if required:
            raise SyntheticDataError(f"{where}: missing time")
        return spec
    if _REL.match(spec):
        return spec
    try:
        datetime.fromisoformat(spec.replace("Z", "+00:00"))
    except ValueError:
        raise SyntheticDataError(f"{where}: bad time '{spec}' (use 'd+N HH:MM' or ISO 8601)") from None
    return spec


def _body_times(body: str, where: str) -> str:
    for m in _WHEN.finditer(body):
        if not _REL.match(m.group(1).strip()):
            raise SyntheticDataError(f"{where}: bad {{when:...}} time '{m.group(1)}' (use 'd+N HH:MM')")
    return body


def _list(cell: str) -> list[str]:
    return [x.strip() for x in cell.split(",") if x.strip()]


def _yes(cell: str) -> bool:
    return cell.strip().lower() in {"yes", "y", "true", "done", "x", "✓"}


def _section(sections: dict[str, _Block], name: str) -> _Block:
    if name not in sections:
        raise SyntheticDataError(f"Missing section '## {name.title()}'")
    return sections[name]


def _unique(items: list[dict], key: str, where: str) -> None:
    seen = set()
    for it in items:
        if it[key] in seen:
            raise SyntheticDataError(f"{where}: duplicate id '{it[key]}'")
        seen.add(it[key])


def parse_world(text: str, known_courses: set[str] | None = None, known_concepts: dict[str, str] | None = None) -> dict:
    """known_courses / known_concepts (id -> course_id) let a pack reference catalog entries imported earlier."""
    s = _blocks(text)
    courses = [{"id": r["id"], "label": r["label"], "domain": r.get("domain", ""), "code": r.get("code", "")}
               for r in _table(s["courses"].lines, "Courses", ["id", "label"])] if "courses" in s else []
    course_ids = {c["id"] for c in courses} | set(known_courses or ())
    concepts = []
    for r in (_table(s["concepts"].lines, "Concepts", ["id", "course", "label"]) if "concepts" in s else []):
        if r["course"] not in course_ids:
            raise SyntheticDataError(f"Concepts row {r['_row']}: unknown course '{r['course']}'")
        concepts.append({"id": r["id"], "course_id": r["course"], "label": r["label"], "aliases": _list(r.get("aliases", ""))})
    _unique(concepts, "id", "Concepts")
    concept_course = dict(known_concepts or {}) | {c["id"]: c["course_id"] for c in concepts}

    def check_concepts(ids: list[str], where: str) -> list[str]:
        bad = [c for c in ids if c not in concept_course]
        if bad:
            raise SyntheticDataError(f"{where}: unknown concept(s) {', '.join(bad)}")
        return ids

    edges = []
    if "concept relations" in s:
        for r in _table(s["concept relations"].lines, "Concept relations", ["source", "relation", "target"]):
            check_concepts([r["source"], r["target"]], f"Concept relations row {r['_row']}")
            edges.append({"source": f"concept:{r['source']}", "target": f"concept:{r['target']}", "relation": r["relation"]})

    student = s.get("student") or _Block("student")
    sfields, _ = _fields_and_body(student.lines)
    subs = {b.title.lower(): b for b in student.subs}
    completed = [{"label": r["course"], "term": r.get("term", "")}
                 for r in _table(subs["completed courses"].lines, "Completed courses", ["course"])] \
        if "completed courses" in subs else []
    seeds = []
    if "self-reports" in subs:
        for r in _table(subs["self-reports"].lines, "Self-reports", ["id", "when", "type", "statement"]):
            where = f"Self-reports row {r['_row']}"
            et = r["type"].strip().lower()
            if et not in {"goal", "interest", "preference", "self_confidence", "mood"}:
                raise SyntheticDataError(f"{where}: unknown type '{r['type']}'")
            cids = check_concepts(_list(r.get("concepts", "")), where)
            payload: dict[str, Any] = {"statement": r["statement"]}
            seed: dict[str, Any] = {"event_id": r["id"], "source": "self_report", "event_type": et, "when": _time(r["when"], where)}
            if et == "self_confidence":
                if len(cids) != 1 or not r.get("value"):
                    raise SyntheticDataError(f"{where}: self_confidence needs exactly one concept and a value")
                payload["value"] = float(r["value"])
                seed |= {"concept_id": cids[0], "course_id": concept_course[cids[0]]}
            else:
                payload["concept_ids"] = cids
            seeds.append(seed | {"payload": payload})
        _unique(seeds, "event_id", "Self-reports")
    profile = {"id": sfields.get("id", "demo_student"), "name": sfields.get("name", "Demo student"),
               "completed_courses": completed, "seed_observations": seeds}

    course_label = {c["id"]: c["label"] for c in courses}
    records: dict[str, list[dict]] = {"canvas": [], "google_calendar": [], "gmail": [], "piazza": [], "edstem": []}
    if "canvas assignments" in s:
        for r in _table(s["canvas assignments"].lines, "Canvas assignments", ["id", "course", "title", "due"]):
            where = f"Canvas assignments row {r['_row']}"
            if r["course"] and r["course"] not in course_ids:
                raise SyntheticDataError(f"{where}: unknown course '{r['course']}' (import its course overview first)")
            records["canvas"].append({
                "external_id": r["id"], "kind": "assignment", "title": r["title"], "body": r.get("description", ""),
                "when": _time(r["due"], where), "course_id": r["course"] or None,
                "concept_ids": check_concepts(_list(r.get("concepts", "")), where),
                "metadata": {"points_possible": float(r["points"]) if r.get("points") else None,
                             "completed": _yes(r.get("done", "")), "course_name": course_label.get(r["course"], r["course"])}})
    if "calendar events" in s:
        for r in _table(s["calendar events"].lines, "Calendar events", ["id", "title", "start", "end"]):
            where = f"Calendar events row {r['_row']}"
            records["google_calendar"].append({
                "external_id": r["id"], "kind": "calendar_event", "title": r["title"], "body": "",
                "when": _time(r["start"], where), "course_id": r.get("course") or None, "concept_ids": [],
                "metadata": {"end": _time(r["end"], where)}})
    if "gmail messages" in s:
        for b in s["gmail messages"].subs:
            f, body = _fields_and_body(b.lines)
            if "id" not in f:
                raise SyntheticDataError(f"Gmail message '{b.title}': missing '- id:' field")
            records["gmail"].append({
                "external_id": f["id"], "kind": "event_announcement", "title": b.title,
                "body": _body_times(body, f"Gmail '{b.title}'"), "when": _time(f.get("sent", ""), f"Gmail '{b.title}'", False), "course_id": None, "concept_ids": check_concepts(_list(f.get("concepts", "")), b.title),
                "metadata": {"from": f.get("from", "")}})
    for section, provider, forum in (("piazza posts", "piazza", "Piazza"), ("ed discussion posts", "edstem", "Ed")):
        if section not in s:
            continue
        for b in s[section].subs:
            f, body = _fields_and_body(b.lines)
            if "id" not in f:
                raise SyntheticDataError(f"{forum} post '{b.title}': missing '- id:' field")
            records[provider].append({
                "external_id": f["id"], "kind": "discussion", "title": b.title, "source_url": f.get("url") or None,
                "body": _body_times(body, f"{forum} '{b.title}'"),
                "when": _time(f.get("posted", ""), f"{forum} '{b.title}'", False),
                "course_id": f.get("course") or None, "concept_ids": check_concepts(_list(f.get("concepts", "")), b.title),
                "metadata": {"is_instructor": f.get("author", "").lower() == "instructor", "type": f.get("type", "")}})
    for provider, items in records.items():
        _unique(items, "external_id", provider)
    return {"courses": courses, "concepts": concepts, "edges": edges, "profile": profile, "records": records}


