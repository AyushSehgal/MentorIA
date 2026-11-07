# MentorIA — Manual Testing Guide

Work through the sections **in order**: MentorIA starts empty and each section adds data the next one relies on.
Each check has **Do** and **Expect**. If something doesn't match, note the check ID (e.g. `A5`) and what you saw.

Demo assets live in `demo_assets/`, are regenerated daily, and use dates relative to today ("d+3" = 3 days from today).

---

## 0. Setup

- [ ] **S1. Start the app.** Do: `./scripts/dev.sh` (stop any older copy first with Ctrl-C). Expect: the API on `:8000` and the UI at http://localhost:5173.
- [ ] **S2. Local model (only for section L).** Do: keep the Ollama app open, or run `ollama serve`, and have `qwen2.5` pulled.
- [ ] **S3. Fast, exact answers.** Do: **Sources → Privacy & AI → Off**. (Local mode rewords answers and is tested in section L.)
- [ ] **S4. Start empty.** Do: **Sources → Reset demo** and confirm. Expect: "MentorIA reset — empty."
- [ ] **S5. Automated checks.** Do: `cd backend && .venv/bin/python -m pytest -q`, then `npm --prefix frontend run build`. Expect: `50 passed`, then `✓ built`.

## E. Empty state

- [ ] **E1. Dashboard.** Expect: only "MentorIA is empty" and an **Add data** button.
- [ ] **E2. Header.** Expect: the title **MentorIA**, grey connector dots, and the student name.
- [ ] **E3. Ask without data.** Do: in the chat **Ask** tab, click "ML topics I'm struggling with?". Expect: "I don't know about any of your courses yet…".
- [ ] **E4. Student Model.** Expect: "No courses yet".

## A. Add data, one asset at a time

Go to **Add data**. After each **Add**, read the inline result (summary and ✓ changes), then glance at the Dashboard.

- [ ] **A1. Step 1, 10-601 course overview.** Expect changes: "Added course Introduction to Machine Learning (10-601)", "19 new concepts", "6 concept relations". The dashboard now shows blocks and tiles: Courses 1, Concepts 19. Student Model lists the concepts with no estimates.
- [ ] **A2. Step 2, 16-831 course overview.** Expect: 16 new concepts and 8 relations. Tiles: Courses 2, Concepts 35.
- [ ] **A3. Step 3, Canvas assignments.** Expect: "Canvas assignments: 7 new". The **Assignments** block shows HW5 (due d+3), HW3 (d+5) and more, with "+N more".
- [ ] **A4. Step 4, my calendar.** Expect: "Calendar events: N new". The **Calendar** block becomes a week grid (today highlighted, red "now" line), with lectures as course-coloured blocks at their times, free time shaded green, and ⏰ deadline chips in day headers (HW5, HW3).
- [ ] **A5. Step 5, 10-601 Quiz 2 (graded).** Expect: "6 graded answers became evidence (3 incorrect: Q2, Q4, Q5)", "Backpropagation: 0.12", "Logistic Regression: 0.30", and "Q7 held for review". Tile: Graded 6.
- [ ] **A6. Ask again.** Do: Ask "ML topics I'm struggling with?". Expect: Backpropagation 0.12 citing p.2 Q4 and Q5, and Logistic Regression 0.30 citing p.1 Q2. The untested-concepts list ends "…and N more", and "1 answer needs review" is noted.
- [ ] **A7. Step 6, 16-831 HW2 (graded).** Expect: Policy Gradients 0.12 and Imitation Learning 0.92. Ask "What robot learning topics am I struggling with?" → Policy Gradients.
- [ ] **A8. Step 7, career goals statement.** Expect: "Learned a new goal: “After graduation I want to work at an early-stage startup that builds robots that understand natural language.”", plus 2 interests and a preference. The Insights block shows **Your goal**.
- [ ] **A9. Step 8, email you sent your advisor.** Expect: "Reinforced goal — now stated in 2 sources". The goal insight shows a **2 sources** pill, and the goal isn't duplicated.
- [ ] **A10. Steps 9–12, emails.** Expect in **Opportunities**:
  - the robotics seminar (VLA) and the startup mixer are on top;
  - the RL reading group's **why?** says it covers a knowledge gap (Policy Gradients);
  - the quant club is at the bottom.
  
  An approval card for the seminar appears in **Needs approval**.
- [ ] **A11. Step 13, Piazza posts.** Expect: **Discussions** shows 3 posts, with instructor posts marked. Mastery is unchanged by the student question.
- [ ] **A12. Step 14, ungraded practice sheet.** Expect: "Indexed … as study material — knowledge estimates unchanged". Mastery numbers are identical to before.
- [ ] **A13. Re-add.** Do: **Add again** on step 5. Expect: "Already added — nothing new was learned from this file."
- [ ] **A14. Order matters, then recovers.** Do: Reset, add step 5 first. Expect a warning: "…couldn't be matched to a known concept… Add the course overview first". Then add step 1, then step 5 again. Expect: the estimates now appear.
- [ ] **A15. Add all remaining.** Do: Reset, then **Add all remaining**. Expect: all 14 added in order, and tiles Courses 2, Concepts 35, Graded 12.

## W. Interactive calendar (after A4–A10)

- [ ] **W1. Navigate.** Do: click **›** then **Today**. Expect: the range moves by a week and back. Days after the imported week are empty.
- [ ] **W2. Event details.** Do: click a lecture block. Expect: a detail panel with its time range, location and Demo label; **×** closes it.
- [ ] **W3. Deadline chip.** Do: click ⏰ HW5. Expect: the due time and course.
- [ ] **W4. Free time.** Do: untick **Free time**. Expect: the green shading disappears. Tick it again, then click a green area. Expect: "Free 12:20 PM–9:00 PM" (or similar) and a **Suggest study blocks** button.
- [ ] **W5. Plan my week.** Do: click **✨ Plan my week**. Expect: "2 study blocks proposed…" and dashed purple blocks appear inside free time, before the HW deadlines. The seminar proposal is dashed on its day at 4 PM.
- [ ] **W6. Approve on the calendar.** Do: click a dashed block, then **Approve** in the panel. Expect: "Simulated — Calendar not connected; nothing written", and the block turns solid purple with ✓.
- [ ] **W7. Reject on the calendar.** Do: click the other dashed block, then **Reject**. Expect: it disappears from the grid.
- [ ] **W8. Overlaps.** Expect: overlapping items sit side by side, not on top of each other.
- [ ] **W9. Phone width.** Do: narrow to ~375 px. Expect: a one-day view with ‹ › stepping a day at a time, and no sideways scroll.

## U. Upload your own files

- [ ] **U1. Your writing.** Do: **Upload**, choose `demo_assets/07_career_goals_statement.pdf`, and tick **I wrote this**. Expect: kind "personal document" and goals learned (or "Already added" if step 7 was added).
- [ ] **U2. Email you received.** Do: upload `demo_assets/09_email_vla_seminar.eml`. Expect: it's added to Opportunities and **no** goals are learned from it.
- [ ] **U3. Unsupported file.** Do: upload a `.txt` or `.png`. Expect the error "Unsupported file type…".
- [ ] **U4. Broken pack.** Do: copy `demo_assets/03_canvas_assignments.md`, change a `course` cell to `nope`, and upload it. Expect an error naming "unknown course". Nothing changes.
- [ ] **U5. Import history.** Expect: every import listed newest first, with a Demo tag on demo files.

## C. Ask tab (questions) — after all 14 assets (A15)

- [ ] **C1. Focus this week?** Expect:
  - priorities: 1. Backpropagation (HW5), 2. Policy Gradients (HW3), …;
  - a "Linked to your goal: **Foundation Models in Robotics** — Project proposal…" line;
  - the free-hours line and the seminar;
  - study-block approval cards at times inside free slots, before the deadlines.
- [ ] **C2. Classes to take next?** Expect:
  - "I don't have a verified course catalog…" and no invented course numbers;
  - your goals, with the main goal showing "(in N sources)";
  - "Courses I know you're taking";
  - goal-related areas;
  - topics to shore up first.
- [ ] **C3. Events to attend?** Expect: the seminar and mixer first with "Matches your stated goal"; "Skipped 1… Quant Finance Club".
- [ ] **C4. "What assignments are due soon?"** Expect: Canvas items due within 7 days, plus instructor Piazza posts.
- [ ] **C5. Sources and caveats.** Expect: answers show source chips (quiz page and question, Canvas, Gmail) and a Caveats list. Hovering the footer shows the intent and trace.

## M. About me tab (student input)

- [ ] **M1. Tabs.** Expect: **Ask** and **About me**, each keeping its own history across page changes.
- [ ] **M2. Prefill chips.** Do: About me → click "My career goal is to ". Expect: the text lands in the input (not sent), with the cursor at the end.
- [ ] **M3. Goal from chat merges.** Do: click the example "I want a job at a startup that makes robots understand language". Expect: ✓ "…now backed by 3 sources", "Connects to: Foundation Models in Robotics, …", and matching opportunities. The goal insight shows **3 sources**.
- [ ] **M4. Interest.** Do: "I'm interested in tactile sensing". Expect: ✓ "Saved interest…".
- [ ] **M5. Preference without the pattern.** Do: "Group study in the evenings works for me". Expect: saved as a preference.
- [ ] **M6. Anything else is a note.** Do: "Robotics competitions are my favorite thing". Expect: ✓ "Saved a note about you…".
- [ ] **M7. Confidence stays separate.** Do: "I'm confident about backpropagation". Expect: "Kept separate from your quiz-based mastery estimates" and a possible blind spot named. On Student Model: mastery is still 0.12, with self-confidence 0.80 and a blind-spot flag.
- [ ] **M8. Mood.** Do: "I'm feeling overwhelmed". Expect: a supportive line and "expires in 24 hours".
- [ ] **M9. Ask doesn't save.** Do: in **Ask**, "Focus this week?". Expect: no ✓ saved list.
- [ ] **M10. About me is instant.** Expect: replies come back immediately even in Local AI mode (no model rewording).

## K. Student Model

- [ ] **K1. Concepts.** Expect two courses, with mastery only where graded evidence exists, self-confidence shown separately, and blind-spot flags.
- [ ] **K2. Goal sources.** Expect the main goal with "stated in 3 sources" and chips: career statement p.1, email you sent, chat.
- [ ] **K3. Correct a goal.** Do: **That's wrong** on the main goal, then Ask "Events to attend?". Expect: the seminar loses "Matches your stated goal" unless another active interest still matches it. Then **Confirm** to restore.
- [ ] **K4. Confidence slider.** Do: move Backpropagation's slider to 0.2. Expect: the blind-spot flag disappears and mastery is unchanged.
- [ ] **K5. Knowledge graph.** Expect both courses, concepts coloured by mastery, and goal nodes linked to Foundation Models in Robotics / Transformers.
- [ ] **K6. History.** Expect belief updates (e.g. Backpropagation — → 0.146 → 0.119) and the observations list.

## P. Approvals

- [ ] **P1. Approve.** Do: on a study block, **Approve**. Expect: "Simulated — Calendar not connected; nothing written".
- [ ] **P2. Reject.** Expect: "Rejected — no external action taken."
- [ ] **P3. Details.** Do: click **details**. Expect: the reason, factor bars and evidence chips.

## L. AI privacy modes

- [ ] **L1. Panel.** Do: **Sources → Privacy & AI**. Expect three options. Local shows qwen2.5 when Ollama is running; Cloud is unavailable without an OpenRouter key.
- [ ] **L2. Local.** Do: select Local and Ask "Focus this week?". Expect: a 5–25 s wait, then either "worded by local:qwen2.5" or a note that the rewrite was discarded (the guardrail).
- [ ] **L3. Ollama off.** Do: quit Ollama and Ask something. Expect: an answer within ~2 s, with "No local model server reachable".
- [ ] **L4. Kept on reset.** Do: Reset demo. Expect: the privacy choice is unchanged.

## R. Resilience & layout

- [ ] **R1. Backend down.** Do: stop the API and reload. Expect: a "Backend unreachable" banner and no crash.
- [ ] **R2. Phone width.** Do: narrow the window to ~375 px. Expect: blocks stack, the chat moves below, and there's no sideways scroll.
- [ ] **R3. No secrets.** Do: `git ls-files | grep -E '\.env$|token|\.db$'`. Expect: no output.

## Finish

- [ ] **Z1.** Reset demo, then choose your AI mode for the presentation (Off is instant; Local tells the privacy story).
