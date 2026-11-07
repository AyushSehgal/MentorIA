# MentorIA synthetic world

All data in this file is **synthetic** (a fictional student, fictional courses, fictional messages).
MentorIA reads it in place of Canvas, Google Calendar, Gmail and Piazza until a real connector is configured.
Every record it produces is labeled "Demo data" in the UI.

**How to edit**
- Change anything below, save, then press **Sync all** in MentorIA (or `POST /api/connectors/sync`). No restart needed.
- Times: `d+3 16:00` means 3 days from today at 16:00 in the student's timezone (`d-1`, `d+0` also work).
  Absolute ISO times such as `2026-11-12T16:00:00-05:00` work too.
- Inside an email or post body, `{when:d+3 16:00}` is replaced by that time written out
  (e.g. "Tuesday, November 10, 2026 at 4:00 PM EST").
- Lists inside a table cell are comma-separated. `ids` must stay unique within a section.
- Self-reports are immutable memory events: to change one, add a new row with a new id.

---

## Courses

| id | label | domain |
|---|---|---|
| systems | Computer Systems (demo course) | systems |
| robot_learning | Intro to Robot Learning (demo course) | robotics |

## Concepts

| id | course | label | aliases |
|---|---|---|---|
| cache_locality | systems | Caches & Locality | cache locality, locality, cache hierarchy, caches |
| cache_coherence | systems | Cache Coherence (MESI) | cache coherence, coherence, mesi, snooping |
| virtual_memory | systems | Virtual Memory & TLBs | virtual memory, tlb, page table, paging, address translation |
| synchronization | systems | Synchronization & Races | synchronization, race condition, mutex, locks, concurrency, semaphore |
| processes_signals | systems | Processes & Signals | processes, signals, fork, exceptional control flow |
| reinforcement_learning | robot_learning | Reinforcement Learning | reinforcement learning, rl, policy gradient, q-learning |
| imitation_learning | robot_learning | Imitation Learning | imitation learning, behavior cloning, learning from demonstration, demonstrations |
| embodied_ai | robot_learning | Embodied AI & Manipulation | embodied ai, embodied, manipulation, robotics, robot, dexterous |

## Concept relations

Illustrative only — not official prerequisites.

| source | relation | target |
|---|---|---|
| cache_locality | prerequisite_of | cache_coherence |
| processes_signals | prerequisite_of | synchronization |
| synchronization | related_to | cache_coherence |
| reinforcement_learning | related_to | imitation_learning |
| imitation_learning | prerequisite_of | embodied_ai |

## Student

- id: demo_student
- name: Alex (demo student)

### Completed courses

| course | term |
|---|---|
| Intro to Programming (demo record) | Fall 2025 |
| Discrete Math (demo record) | Spring 2026 |
| Linear Algebra (demo record) | Spring 2026 |

### Self-reports

`type` is one of: goal, interest, preference, self_confidence, mood. `value` (0–1) is used only for self_confidence.
`concepts` links goals/interests to concepts; for self_confidence it names the single concept rated.

| id | when | type | concepts | value | statement |
|---|---|---|---|---|---|
| obs_seed_goal_embodied | d-14 10:00 | goal | embodied_ai, imitation_learning, reinforcement_learning | | I want to do research in embodied AI / robotics, ideally manipulation. |
| obs_seed_pref_visual | d-14 10:05 | preference | | | Prefers short, focused study blocks (25–50 min) in the afternoon. |
| obs_seed_conf_coherence | d-10 18:00 | self_confidence | cache_coherence | 0.85 | I'm pretty confident about cache coherence. |
| obs_seed_conf_sync | d-10 18:01 | self_confidence | synchronization | 0.6 | Synchronization is okay. |
| obs_seed_conf_vm | d-10 18:02 | self_confidence | virtual_memory | 0.5 | Not sure about virtual memory. |

---

## Canvas assignments

| id | course | title | due | concepts | points | done | description |
|---|---|---|---|---|---|---|---|
| canvas_a1 | systems | Cache Lab Part B: coherence simulator | d+4 23:59 | cache_locality, cache_coherence | 100 | no | Implement a MESI snooping coherence simulator and report invalidation counts. |
| canvas_a2 | systems | Proxy Lab checkpoint: concurrent proxy | d+9 23:59 | synchronization | 50 | no | Add thread-safe caching to your proxy. |
| canvas_a3 | robot_learning | HW3: Behavior cloning from demonstrations | d+3 23:59 | imitation_learning | 100 | no | Train a behavior cloning policy on the provided demonstrations. |
| canvas_a4 | systems | Reading response: virtual memory paper | d-1 23:59 | virtual_memory | 10 | yes | One-page response. |
| canvas_a5 | robot_learning | Project proposal: embodied manipulation agent | d+12 23:59 | embodied_ai | 20 | no | Two-page proposal. |

## Calendar events

| id | title | start | end | course |
|---|---|---|---|---|
| cal_e1 | Dinner with friends | d+0 19:00 | d+0 21:00 | |
| cal_e2 | Computer Systems lecture | d+1 10:00 | d+1 11:20 | systems |
| cal_e3 | Robot Learning lecture | d+1 14:00 | d+1 15:20 | robot_learning |
| cal_e4 | Campus job shift | d+1 17:00 | d+1 20:00 | |
| cal_e5 | Research group meeting | d+2 13:00 | d+2 14:00 | |
| cal_e6 | Systems TA office hours | d+2 16:00 | d+2 17:00 | systems |
| cal_e7 | Computer Systems lecture | d+3 10:00 | d+3 11:20 | systems |
| cal_e8 | Robot Learning lecture | d+3 14:00 | d+3 15:20 | robot_learning |
| cal_e9 | Robotics lab hours | d+4 09:00 | d+4 12:00 | |

## Gmail messages

Each `###` heading is the subject line. Fields come first, then a blank line, then the body.

### Robotics Seminar: Learning Dexterous Manipulation from Human Video
- id: gmail_m1
- from: robotics-seminars@example.edu
- sent: d-1 09:12

Robotics Seminar Series
Speaker: Dr. Jordan Rivera (Example Robotics Lab)
Title: Learning Dexterous Manipulation from Human Video
When: {when:d+3 16:00}
Where: Robotics Seminar Room 1305 (demo venue)
Zoom: https://example.edu/seminar/manipulation
Abstract: How can robots acquire manipulation skills by watching people? This talk covers imitation learning from video and embodied AI benchmarks.

### Call for undergraduate research assistants — Embodied AI Lab
- id: gmail_m2
- from: embodied-ai-lab@example.edu
- sent: d-2 15:40

The Embodied AI Lab is recruiting undergraduate research assistants for the spring term to work on robot manipulation and imitation learning. Reply with a CV and a short statement of interest. Applications are reviewed on a rolling basis.

### Career Fair: Finance & Consulting
- id: gmail_m3
- from: careers@example.edu
- sent: d-3 08:00

Meet recruiters from finance and consulting firms.
When: {when:d+5 11:00}
Where: University Center Ballroom (demo venue)

### Systems Reading Group: Cache coherence in modern GPUs
- id: gmail_m4
- from: systems-reading@example.edu
- sent: d-1 12:30

This week's systems reading group discusses cache coherence protocols in GPUs.
When: {when:d+6 12:00}
Where: CS Lounge (demo venue)

## Piazza posts

Each `###` heading is the post title. `author` is `instructor` or `student`.

### Cache Lab: clarification on MESI state transitions
- id: piazza_p1
- course: systems
- posted: d-1 17:20
- author: instructor
- type: announcement
- concepts: cache_coherence

Several of you asked whether a BusRdX from another core should move a line from S to I. Yes — see the updated state diagram in the handout.

### Why does my coherence simulator double-count invalidations?
- id: piazza_p2
- course: systems
- posted: d-1 21:05
- author: student
- type: question
- concepts: cache_coherence

My invalidation count is 2x the reference trace. Am I counting both the request and the snoop?

### HW3 reminder + extra office hours
- id: piazza_p3
- course: robot_learning
- posted: d-2 10:00
- author: instructor
- type: announcement
- concepts: imitation_learning

HW3 is due this week. Extra office hours Thursday afternoon.
