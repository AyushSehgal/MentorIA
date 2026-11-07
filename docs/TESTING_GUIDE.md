# MentorIA — Manual Testing Guide

Work through the sections **in order**. MentorIA starts **prepopulated** with three courses (10-601, 16-831, 10-605) and a week of sample data.
Each check has **Do** and **Expect**. If something doesn't match, note the check ID (e.g. `A5`) and what you saw.

Demo assets live in `demo_assets/`, are regenerated daily, and use dates relative to today ("d+3" = 3 days from today).

---

## 0. Setup

- [ ] **S1. Start the app.** Do: `./scripts/dev.sh` (stop any older copy first with Ctrl-C). Expect: the API on `:8000` and the UI at http://localhost:5173.
- [ ] **S2. Local model (only for section L).** Do: keep the Ollama app open, or run `ollama serve`, and have `qwen2.5` pulled.
- [ ] **S3. Fast, exact answers.** Do: **Sources → Privacy & AI → Off**. (Local mode rewords answers and is tested in section L.)
- [ ] **S4. Starting data.** Do: **Sources → Reset** and confirm. Expect: "Reset — starting data restored."
- [ ] **S5. Automated checks.** Do: `cd backend && .venv/bin/python -m pytest -q`, then `npm --prefix frontend run build`. Expect: `52 passed`, then `✓ built`.

## E. Prepopulated start

- [ ] **E1. Dashboard.** Expect a **Quick Recap** button (with "3 suggestions"), then three blocks only: Calendar, Assignments, and Relevant Discussion.
- [ ] **E1b. Quick Recap.** Do: click **Quick Recap**. Expect up to four boxes: Your goal ("Stated in 2 places"), Focus this week (Backpropagation · Policy Gradients), Due next (HW5) and, only when there's a blind spot, Watch out. **Hide recap** closes them.
- [ ] **E1c. Suggested for you.** Expect three boxes under **Suggested for you**:
  - **From your Gmail:** the robotics seminar, with **Add to calendar** / **Not now**;
  - **From the 16-831 reading list:** SayCan, with **Open paper** (arXiv) / **Dismiss**;
  - **A classmate shared this on Piazza:** RT-2, with **Open** / **Dismiss**.
- [ ] **E1d. Dismiss a paper.** Do: **Dismiss** SayCan. Expect: "Dismissed", then the next paper from the same real reading list (Code as Policies) takes its place.
- [ ] **E1e. Add the seminar.** Do: **Add to calendar**. Expect: "✓ Added to your plan (calendar not connected, nothing written)", then the box leaves; the seminar shows as a solid ✓ block in **Open calendar**.
- [ ] **E2. Clean UI.** Expect: no "Add data" tab, and no text anywhere saying "demo".
- [ ] **E3. Your goal.** Expect: the Your goal box reads "…startup that builds robots that understand natural language", "Stated in 2 places".
- [ ] **E4. Three courses.** Do: open **Student Model**. Expect: 10-601, 16-831 and 10-605.

## O. Course overlap (10-601 ↔ 10-605)

- [ ] **O1. Shared concepts.** Expect: under 10-605, Linear Regression, Optimization & SGD, Neural Networks, Backpropagation, Transformers & Language Models and Recommender Systems each show **shared with 10-601**. Under 10-601 they show **shared with 10-605**.
- [ ] **O2. Evidence combines.** Expect: Backpropagation = 0.12 from **3** graded answers, with chips 10-601 Quiz 2 p.2 Q4, Q5 and 10-605 lecture quizzes p.1 Q1.
- [ ] **O3. Ask about 10-605.** Do: Ask "What 10-605 topics am I struggling with?". Expect: Backpropagation (citing both courses), Distributed Learning & All-Reduce 0.15, and Bloom Filters & Count-Min Sketch 0.15.
- [ ] **O4. Graph.** Expect: the Backpropagation node is linked from both the 10-601 and 10-605 course nodes.

## D. Dashboard blocks

- [ ] **D1. Assignments tags.** Expect each row to show a coloured course tag (10-601 / 10-605 / 16-831) and a deadline tag (e.g. "Tue, Nov 10"; the time appears only when it isn't 11:59 PM, e.g. Exam 2 "· 7:00 PM"). Submitted work shows "submitted".
- [ ] **D2. Sort.** Do: click **Course**. Expect: groups per course with the full course name, each sorted by deadline. Click **Deadline** to get one list again.
- [ ] **D2b. Complete toggle.** Do: click the round button at the start of HW5. Expect: it turns into a green ✓, the title is struck through, and the tag reads "done". The row stays in place. **Quick Recap → Due next** moves on to the next assignment. Click the button again to undo. Reload: completed items sit at the bottom; the choice is kept across reloads and re-syncs.
- [ ] **D3. Assignment details.** Do: click HW5. Expect: course, due date and time, points, description.
- [ ] **D4. Relevant Discussion.** Expect it collapsed by default: one line of course tags with post counts and a **Show N ▾** button. Click it. Expect posts grouped by course. Each post is tagged **Piazza**, **Ed** or **Email**, and instructor/staff posts are marked and listed first. The [10-601] Exam 2 email appears here, tagged Email · Staff.
- [ ] **D5. Gone.** Expect: no Opportunities block and no Documents block. Gmail events still appear in Quick Recap → Suggested for you.

## W. Interactive calendar

- [ ] **W0. Open it.** Do: click **Open calendar**, or any day in the strip. Expect: the full week grid; **Close** returns to the strip.
- [ ] **W1. Navigate.** Do: click **›** then **Today**. Expect: the range moves by a week and back. Days after the imported week are empty.
- [ ] **W2. Event details.** Do: click a lecture block. Expect: a detail panel with its time range, location and Demo label; **×** closes it.
- [ ] **W3. Deadline chip.** Do: click ⏰ HW5. Expect: the due time and course.
- [ ] **W4. Free time.** Do: untick **Free time**. Expect: the green shading disappears. Tick it again, then click a green area. Expect: "Free 12:20 PM–9:00 PM" (or similar) and a **Suggest study blocks** button.
- [ ] **W5. Plan my week.** Do: click **✨ Plan my week**. Expect: "2 study blocks proposed…" and dashed purple blocks appear inside free time, before the HW deadlines. The seminar proposal is dashed on its day at 4 PM.
- [ ] **W6. Approve on the calendar.** Do: click a dashed block, then **Approve** in the panel. Expect: "Simulated — Calendar not connected; nothing written", and the block turns solid purple with ✓.
- [ ] **W7. Reject on the calendar.** Do: click the other dashed block, then **Reject**. Expect: it disappears from the grid.
- [ ] **W8. Overlaps.** Expect: overlapping items sit side by side, not on top of each other.
- [ ] **W9. Phone width.** Do: narrow to ~375 px. Expect: a one-day view with ‹ › stepping a day at a time, and no sideways scroll.

## C. Ask tab (questions)

- [ ] **C1. Focus this week?** Expect a short answer in this shape:
  - "Given your 10-601 Quiz 2 — you got the neural networks question right (Q3) but missed both backpropagation questions (Q4 and Q5), and your 10-605 lecture quizzes agree — I'd make **Backpropagation** your focus this week."
  - "Your next 10-601 lecture is "Backpropagation I" (Mon …), and Homework 5 is due Tue …"
  - "Review before then:" Goodfellow et al. §6.5 and Bishop §5.3 (suggested readings, not course-assigned)
  - "Also this week: **Policy Gradients** for HW3 …" and a drafted 50-minute study block to approve.
  - Appears instantly in every AI mode (this answer is never reworded).
- [ ] **C2. Classes to take next?** Expect:
  - "I don't have a verified course catalog…" and no invented course numbers;
  - your goals, with the main goal showing "(in N sources)";
  - "Courses I know you're taking";
  - goal-related areas;
  - topics to shore up first.
- [ ] **C3. Events to attend?** Expect: the seminar and mixer first with "Matches your stated goal"; "Skipped 1… Quant Finance Club".
- [ ] **C4. "What assignments are due soon?"** Expect: Canvas items due within 7 days, plus instructor Piazza posts.
- [ ] **C5. Sources and caveats.** Expect: answers show source chips (quiz page and question, Canvas, Gmail) and a Caveats list. No status footer is shown under answers.

## M. About me tab (student input)

- [ ] **M1. Tabs.** Expect: **Ask** and **About me**, each keeping its own history across page changes.
- [ ] **M2. Prefill chips.** Do: About me → click "My career goal is to ". Expect: the text lands in the input (not sent), with the cursor at the end.
- [ ] **M3. Goal from chat merges.** Do: in About me, click the example "I want a job at a startup that makes robots understand language". Expect: ✓ "…now backed by 3 sources", "Connects to: Foundation Models in Robotics, …", and matching opportunities. The goal insight shows **3 sources**.
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
- [ ] **L2. Local.** Do: select Local and Ask "Classes to take next?". Expect: a 5–25 s wait while the local model words the answer. (Which model produced an answer is no longer shown in the chat; the API still reports it in `llm_used` / `llm_provider`.)
- [ ] **L3. Ollama off.** Do: quit Ollama and Ask something. Expect: an answer within ~2 s, with "No local model server reachable".
- [ ] **L4. Kept on reset.** Do: Reset. Expect: the privacy choice is unchanged.

## T. Dark mode

- [ ] **T1. Follows the system.** Expect: with no saved choice, MentorIA matches your OS light/dark setting on load, with no white flash.
- [ ] **T2. Toggle.** Do: click ☾ / ☀︎ next to your name. Expect: the whole app switches, including Quick Recap boxes, tags, the calendar grid and the Student Model map. Text stays readable everywhere.
- [ ] **T3. Remembered.** Do: reload. Expect: your choice is kept.

## R. Resilience & layout

- [ ] **R1. Backend down.** Do: stop the API and reload. Expect: a "Backend unreachable" banner and no crash.
- [ ] **R2. Phone width.** Do: narrow the window to ~375 px. Expect: blocks stack, the chat moves below, and there's no sideways scroll.
- [ ] **R3. No secrets.** Do: `git ls-files | grep -E '\.env$|token|\.db$'`. Expect: no output.

## Finish

- [ ] **Z1.** Reset, then choose your AI mode for the presentation (Off is instant; Local tells the privacy story).
