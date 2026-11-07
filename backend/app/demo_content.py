"""Generate MentorIA's sample data files (demo_assets/), imported automatically on first start and on reset.

Courses: 10-601 Introduction to Machine Learning, 16-831 Introduction to Robot Learning and 10-605 ML with Large
Datasets (CMU). Concept lists follow the lecture topics on the public course pages:
  https://www.cs.cmu.edu/~mgormley/courses/10601/   https://16-831-s24.github.io/   https://10605.github.io/
10-605 shares several concepts with 10-601 (optimization, linear regression, backprop/autodiff, neural nets,
transformers, matrix factorization): they are ONE concept taught in both courses, so evidence from either applies.
Everything else — the student, grades, emails, events, speakers and dates — is fictional sample content. Files carry
the hidden marker MENTORIA-DEMO-ASSET (PDF metadata, email header, .ics property, .md comment) so the API keeps
is_fixture=True; nothing visible says "demo". Dates are relative to the day the assets are generated.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from email.message import EmailMessage
from email.utils import format_datetime, make_msgid
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from .config import REPO_ROOT, settings

OUT = REPO_ROOT / "demo_assets"
MARK = "MENTORIA-DEMO-ASSET"
SAMPLE_NOTE = "Sample document prepared for MentorIA - not an official course document."

ML = {
    "id": "10-601", "code": "10-601", "title": "Introduction to Machine Learning", "domain": "ml",
    "aka": "intro to ml, machine learning, ml, 10-301, 10601",
    "source": "https://www.cs.cmu.edu/~mgormley/courses/10601/",
    "concepts": [
        ("Decision Trees", "decision_trees", "ID3, information gain, entropy, mutual information"),
        ("k-NN & Model Selection", "knn_model_selection", "k-nearest neighbor, knn, cross-validation, hyperparameters"),
        ("Perceptron", "perceptron", "perceptron algorithm, linear separability"),
        ("Linear Regression", "linear_regression", "least squares, normal equations, mean squared error"),
        ("Optimization & SGD", "optimization_sgd", "gradient descent, stochastic gradient descent, sgd, convexity, learning rate"),
        ("Logistic Regression", "logistic_regression", "sigmoid, log-loss, cross-entropy, conditional likelihood"),
        ("Feature Engineering & Regularization", "regularization", "l2 regularization, l1 regularization, overfitting, feature engineering"),
        ("Neural Networks", "neural_networks", "multilayer perceptron, mlp, activation function, hidden layer"),
        ("Backpropagation", "backpropagation", "backprop, chain rule, computation graph, automatic differentiation"),
        ("Societal Impacts of ML", "societal_impacts", "fairness, ethics of ml"),
        ("PAC Learning", "pac_learning", "learning theory, sample complexity, vc dimension"),
        ("MLE & MAP", "mle_map", "maximum likelihood, map estimation"),
        ("CNNs & RNNs", "cnns_rnns", "convolutional neural network, cnn, recurrent neural network, rnn"),
        ("Transformers & Language Models", "transformers_lms",
         "transformer, transformers, self-attention, language model, language models, pre-training, fine-tuning, llm"),
        ("Reinforcement Learning (MDPs)", "ml_reinforcement_learning", "markov decision process, mdps, deep rl"),
        ("Ensemble Methods", "ensembles", "boosting, bagging, adaboost, random forest"),
        ("K-Means & PCA", "kmeans_pca", "k-means, clustering, pca, dimensionality reduction"),
        ("Recommender Systems", "recommender_systems", "collaborative filtering, matrix factorization"),
        ("Generative Models for Vision", "generative_vision", "diffusion model, gan, generative model"),
    ],
    "relations": [
        ("optimization_sgd", "logistic_regression", "prerequisite_of"),
        ("logistic_regression", "neural_networks", "prerequisite_of"),
        ("neural_networks", "backpropagation", "prerequisite_of"),
        ("backpropagation", "cnns_rnns", "prerequisite_of"),
        ("cnns_rnns", "transformers_lms", "prerequisite_of"),
        ("mle_map", "logistic_regression", "related_to"),
    ],
    # Standard texts suggested by MentorIA (not claimed as assigned by the course).
    "readings_header": "Suggested readings (standard texts chosen by MentorIA, not assigned by the course):",
    "readings": [
        ("Goodfellow, Bengio & Courville, Deep Learning, Sec. 6.5: Back-Propagation and Other Differentiation Algorithms",
         "https://www.deeplearningbook.org/contents/mlp.html", "backpropagation, neural_networks"),
        ("Bishop, Pattern Recognition and Machine Learning, Sec. 5.3: Error Backpropagation",
         "", "backpropagation"),
    ],
}

RL = {
    "id": "16-831", "code": "16-831", "title": "Introduction to Robot Learning", "domain": "robotics",
    "aka": "robot learning, intro to robot learning, 16831",
    "source": "https://16-831-s24.github.io/",
    "concepts": [
        ("Imitation Learning", "imitation_learning", "behavior cloning, dagger, learning from demonstrations, mdp basics"),
        ("Value & Policy Iteration", "value_policy_iteration", "value iteration, policy iteration, bellman equation"),
        ("Q-Learning", "q_learning", "q-learning, dqn, deep q-network, temporal difference"),
        ("Policy Gradients", "policy_gradients", "policy gradient, reinforce, score function, likelihood ratio"),
        ("Actor-Critic Methods", "actor_critic", "actor-critic, advantage function, a2c"),
        ("Advanced RL (PPO, SAC)", "advanced_rl", "ppo, trpo, sac, soft actor-critic"),
        ("Optimal Control & Planning", "optimal_control", "model-based control, lqr, mpc, trajectory optimization"),
        ("Deep Model-Based RL", "model_based_rl", "model-based rl, world model, world models, learned dynamics"),
        ("Offline RL", "offline_rl", "offline reinforcement learning, batch rl"),
        ("Inverse RL", "inverse_rl", "inverse reinforcement learning, irl, reward learning"),
        ("Bandits & Preference-Based Learning", "bandits_preferences", "multi-armed bandit, preference learning, rlhf"),
        ("Exploration", "exploration", "exploration bonus, curiosity, intrinsic motivation"),
        ("Simulation & Sim2Real", "sim2real", "sim-to-real, sim2real, domain randomization"),
        ("Safe Robot Learning", "safe_rl", "safe rl, safety constraints, constrained mdp"),
        ("Multi-Task & Transfer Learning", "multitask_transfer", "multi-task, meta-learning, transfer learning"),
        ("Foundation Models in Robotics", "foundation_models_robotics",
         "foundation models, vision-language-action, vla, language-conditioned, natural language, language, saycan, rt-1"),
    ],
    "relations": [
        ("value_policy_iteration", "q_learning", "prerequisite_of"),
        ("policy_gradients", "actor_critic", "prerequisite_of"),
        ("actor_critic", "advanced_rl", "prerequisite_of"),
        ("optimal_control", "model_based_rl", "prerequisite_of"),
        ("imitation_learning", "inverse_rl", "related_to"),
        ("imitation_learning", "foundation_models_robotics", "related_to"),
        ("ml_reinforcement_learning", "policy_gradients", "related_to"),
        ("transformers_lms", "foundation_models_robotics", "prerequisite_of"),
    ],
    # Readings listed on the public course page for Lecture 24 "Foundation Models in Robotics".
    "readings": [
        ("Do As I Can, Not As I Say: Grounding Language in Robotic Affordances (SayCan)",
         "https://arxiv.org/abs/2204.01691", "foundation_models_robotics"),
        ("RT-1: Robotics Transformer for Real-World Control at Scale",
         "https://arxiv.org/abs/2212.06817", "foundation_models_robotics, imitation_learning"),
        ("CLIPort: What and Where Pathways for Robotic Manipulation",
         "https://arxiv.org/abs/2109.12098", "foundation_models_robotics, imitation_learning"),
        ("Code as Policies: Language Model Programs for Embodied Control",
         "https://arxiv.org/abs/2209.07753", "foundation_models_robotics, transformers_lms"),
    ],
}


LD = {
    "id": "10-605", "code": "10-605", "title": "Machine Learning with Large Datasets", "domain": "ml",
    "aka": "ml with large datasets, machine learning with large datasets, large datasets, mlld, 10-405, 10-805, 10605",
    "source": "https://10605.github.io/",
    "concepts": [
        ("Map-Reduce & Spark", "mapreduce_spark", "map-reduce, mapreduce, spark, dataflow, workflows"),
        ("Distributed Learning & All-Reduce", "distributed_learning", "parameter mixing, all-reduce, allreduce, data parallelism, distributed sgd"),
        ("Sparsity & Hash Kernels", "hash_kernels", "hashing trick, feature hashing, hash kernel, hash kernels"),
        ("Bloom Filters & Count-Min Sketch", "sketches", "bloom filter, bloom filters, count-min sketch, sketching"),
        ("Locality-Sensitive Hashing", "lsh", "locality sensitive hashing, lsh, minhash, simhash"),
        ("Parallel Optimization with GPUs", "gpu_optimization", "gpu, gpus, parallel optimization"),
        ("LoRA & Hyperparameter Search", "lora", "low-rank adaptation, lora, bpe, hyperparameter search"),
        ("Embarrassingly Parallel Training", "parallel_training", "embarrassingly parallel, parallel training"),
        ("Model Compression & Pruning", "model_compression", "model compression, pruning, quantization, distillation"),
        ("KV Caching for LLMs", "kv_caching", "kv cache, kv caching, kv-caching"),
        ("Contrastive Learning & Retrieval", "contrastive_retrieval", "contrastive learning, dense retrieval, embedding retrieval"),
        ("Retrieval-Augmented Generation", "rag", "retrieval-augmented generation, rag"),
        ("Scalable Evaluation", "scalable_evaluation", "network effects, scalable evaluation"),
    ],
    # Concepts 10-605 teaches that 10-601 already defines: one concept, shared evidence.
    "shared": [
        ("optimization_sgd", "Learning as Optimization"),
        ("linear_regression", "HW2 Parallel Linear Regression"),
        ("backpropagation", "Autodiff"),
        ("neural_networks", "Deep Learning: Background and Architectures"),
        ("transformers_lms", "Deep Learning: Transformers"),
        ("recommender_systems", "matrix factorization at scale"),
    ],
    "relations": [
        ("mapreduce_spark", "distributed_learning", "prerequisite_of"),
        ("optimization_sgd", "distributed_learning", "prerequisite_of"),
        ("hash_kernels", "lsh", "related_to"),
        ("transformers_lms", "lora", "prerequisite_of"),
        ("transformers_lms", "kv_caching", "prerequisite_of"),
        ("model_compression", "kv_caching", "related_to"),
        ("contrastive_retrieval", "rag", "prerequisite_of"),
        ("backpropagation", "gpu_optimization", "related_to"),
    ],
}


# ---- helpers ----------------------------------------------------------------------------
def _at(base: date, days: int, hh: int, mm: int = 0) -> datetime:
    d = base + timedelta(days=days)
    return datetime(d.year, d.month, d.day, hh, mm, tzinfo=settings.tz)


def _human(dt: datetime) -> str:
    return dt.strftime("%A, %B %-d, %Y at %-I:%M %p ") + (dt.tzname() or "")


class _Pdf:
    def __init__(self, path: Path, title: str, subtitle: str):
        self.c = canvas.Canvas(str(path), pagesize=letter)
        self.c.setSubject(MARK)  # hidden sample-data marker (is_fixture), never rendered
        self.c.setAuthor(settings.student_name)
        self.title, self.subtitle, self.page = title, subtitle, 0
        self._new_page()

    def _new_page(self):
        if self.page:
            self.c.showPage()
        self.page += 1
        c = self.c
        c.setFont("Helvetica-Bold", 14)
        c.drawString(54, 742, self.title)
        c.setFont("Helvetica", 9)
        c.drawString(54, 728, self.subtitle)
        c.setFillColorRGB(0.45, 0.45, 0.45)
        c.drawString(54, 715, SAMPLE_NOTE)
        c.setFillColorRGB(0, 0, 0)
        self.y = 692

    def line(self, text: str, size: float = 10, bold: bool = False, gap: float = 4, fit: bool = False):
        font = "Helvetica-Bold" if bold else "Helvetica"
        if fit:  # parse-critical lines never wrap: shrink the font instead
            while stringWidth(text, font, size) > 504 and size > 5.5:
                size -= 0.25
            lines = [text]
        else:
            lines, cur = [], ""
            for w in text.split():
                if stringWidth((cur + " " + w).strip(), font, size) > 504:
                    lines.append(cur)
                    cur = w
                else:
                    cur = (cur + " " + w).strip()
            lines.append(cur)
        for ln in lines:
            if self.y < 60:
                self._new_page()
            self.c.setFont(font, size)
            self.c.drawString(54, self.y, ln)
            self.y -= size + gap

    def space(self, h: float = 8):
        self.y -= h

    def new_page(self):
        self._new_page()

    def save(self):
        self.c.save()


# ---- assets -----------------------------------------------------------------------------
def course_overview(course: dict, path: Path):
    p = _Pdf(path, f"{course['code']} {course['title']} - Course overview",
             f"Prepared for MentorIA from the public course page: {course['source']}")
    p.line(f"Course: {course['code']} {course['title']}", fit=True)
    p.line(f"Course ID: {course['id']}", fit=True)
    p.line(f"Domain: {course['domain']}", fit=True)
    p.line(f"Also known as: {course['aka']}", fit=True)
    p.line(f"Source: {course['source']}", fit=True)
    p.space()
    p.line("Concepts (lecture topics from the public schedule; aliases help MentorIA recognize them in your files):", bold=True)
    for label, cid, aliases in course["concepts"]:
        p.line(f"Concept: {label} | id: {cid} | aliases: {aliases}", size=8.5, gap=3, fit=True)
    if course.get("shared"):
        p.space()
        p.line("Topics shared with other courses (MentorIA links them to the same concept):", bold=True)
        for cid, note in course["shared"]:
            p.line(f"Shared concept: {cid} | taught here as: {note}", size=8.5, gap=3, fit=True)
    if course.get("readings"):
        p.space()
        p.line(course.get("readings_header", "Reading list (from the course page):"), bold=True)
        for title, url, concepts in course["readings"]:
            link = f" | url: {url}" if url else ""
            p.line(f"Reading: {title}{link} | concepts: {concepts}", size=8, gap=3, fit=True)
    p.space()
    p.line("How topics build on each other (MentorIA annotation, not official prerequisites):", bold=True)
    for a, b, rel in course["relations"]:
        p.line(f"Relation: {a} -> {b} | {rel}", size=8.5, gap=3, fit=True)
    p.save()


def graded(path: Path, title: str, course: dict, when: date, total: str, pages: list[list[tuple]]):
    p = _Pdf(path, title, f"Student: {settings.student_name}   Graded feedback")
    p.line(f"Course: {course['code']} {course['title']}", fit=True)
    p.line(f"Date: {when.isoformat()}   Total: {total}", fit=True)
    for i, page in enumerate(pages):
        if i:
            p.new_page()
        for q, topic, prompt, ans, result, score, comment in page:
            p.space(6)
            p.line(f"Q{q}.", bold=True, gap=2)
            p.line(f"Topic: {topic}", fit=True, gap=2)
            p.line(f"Question: {prompt}", gap=2)
            p.line(f"Student answer: {ans}", fit=True, gap=2)
            if result:
                p.line(f"Result: {result}", fit=True, gap=2)
            p.line(f"Score: {score}", fit=True, gap=2)
            if comment:
                p.line(f"Grader comment: {comment}", gap=2)
    p.save()


def personal_statement(path: Path):
    p = _Pdf(path, "Career goals - personal statement (draft)", f"Author: {settings.student_name}")
    p.line("Document type: personal statement", fit=True)
    p.space()
    for para in [
        "I came to CMU because I like building things that move. This semester I am taking 10-601 Introduction to Machine "
        "Learning and 16-831 Introduction to Robot Learning.",
        "After graduation I want to work at an early-stage startup that builds robots that understand natural language.",
        "I am especially interested in vision-language-action models and language-conditioned manipulation.",
        "I'm also interested in how transformers and language models can turn spoken instructions into robot plans.",
        "I prefer project-based learning and short, focused study blocks in the afternoon.",
        "Over the next year I plan to build a small prototype where a robot arm follows instructions like \"put the red cup "
        "on the shelf\", and to meet founders working on this problem.",
    ]:
        p.line(para)
        p.space(6)
    p.save()


def practice_sheet(path: Path):
    p = _Pdf(path, "10-601 Practice problems: Neural Networks (no solutions)", "Question sheet only - no answers or grades")
    p.line(f"Course: {ML['code']} {ML['title']}", fit=True)
    for q, topic, prompt in [
        (1, "Neural Networks", "Why does a network with only linear activations collapse to a linear model?"),
        (2, "Backpropagation", "Write the gradient of the loss with respect to the first-layer weights for a 2-layer MLP."),
        (3, "Backpropagation", "Why do we cache forward-pass values when running backpropagation?"),
    ]:
        p.space(6)
        p.line(f"Q{q}.", bold=True, gap=2)
        p.line(f"Topic: {topic}", fit=True, gap=2)
        p.line(prompt)
    p.save()


def write_email(path: Path, sender: str, to: str, subject: str, body: str, sent: datetime):
    m = EmailMessage()
    m["From"], m["To"], m["Subject"] = sender, to, subject
    m["Date"] = format_datetime(sent)
    m["Message-ID"] = make_msgid(idstring=path.stem, domain="mentoria.example")
    m["X-MENTORIA"] = MARK
    m.set_content(body)
    path.write_bytes(bytes(m))


def ics(path: Path, today: date):
    def stamp(dt: datetime) -> str:
        return dt.strftime("%Y%m%dT%H%M%S")

    topics = {
        "10-601": iter(["Backpropagation I", "Backpropagation II", "Societal Impacts of ML", "PAC Learning"]),
        "16-831": iter(["Policy Gradient Methods", "Actor-Critic Methods", "Advanced RL Algorithms"]),
        "10-605": iter(["KV Caching and Model Compression Recap", "Contrastive Learning and Retrieval",
                        "RAG / Optimizing Transformer Architectures"]),
    }
    nxt = lambda code: next(topics[code], "lecture")  # noqa: E731
    events = []
    for d in range(0, 8):
        day = today + timedelta(days=d)
        wd = day.weekday()  # 0=Mon
        if wd in (0, 2, 4):
            events.append((f"10-601 lecture: {nxt('10-601')}", d, 11, 0, 12, 20, "Lecture hall"))
        if wd in (0, 2):
            events.append((f"16-831 lecture: {nxt('16-831')}", d, 9, 30, 10, 50, "Lecture hall"))
            events.append((f"10-605 lecture: {nxt('10-605')}", d, 15, 30, 16, 50, "Lecture hall"))
        if wd == 1:
            events.append(("16-831 office hours", d, 11, 0, 11, 45, "Faculty office"))
            events.append(("Campus job shift", d, 17, 0, 20, 0, ""))
        if wd == 3:
            events.append(("Campus job shift", d, 17, 0, 20, 0, ""))
            events.append(("Coffee chat with a robotics startup founder", d, 15, 0, 15, 45, "Campus cafe"))
        if wd == 4:
            events.append(("10-601 recitation", d, 14, 0, 15, 0, "Recitation room"))
            events.append(("10-605 recitation", d, 15, 30, 16, 50, "Recitation room"))
        if wd == 5:
            events.append(("Robotics club build session", d, 13, 0, 16, 0, "Makerspace"))
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//MentorIA demo//EN", f"X-MENTORIA:{MARK}"]
    for i, (title, d, h1, m1, h2, m2, loc) in enumerate(events):
        s, e = _at(today, d, h1, m1), _at(today, d, h2, m2)
        lines += ["BEGIN:VEVENT", f"UID:mentoria-{i}-{s.strftime('%Y%m%d%H%M')}@mentoria.example",
                  f"DTSTART;TZID={settings.timezone}:{stamp(s)}", f"DTEND;TZID={settings.timezone}:{stamp(e)}",
                  f"SUMMARY:{title}", f"LOCATION:{loc}", "END:VEVENT"]
    lines.append("END:VCALENDAR")
    path.write_text("\r\n".join(lines) + "\r\n")


CANVAS_PACK = f"""<!-- {MARK} -->
# Canvas export

Sample assignments for this week. 10-601 and 10-605 titles follow their public homework lists; dates, points and 16-831
homework topics are sample content.

## Canvas assignments

| id | course | title | due | concepts | points | done | description |
|---|---|---|---|---|---|---|---|
| c601_hw4 | 10-601 | Homework 4: Logistic Regression | d-3 23:59 | logistic_regression | 100 | yes | Written + programming. |
| c601_hw5 | 10-601 | Homework 5: Neural Networks | d+3 23:59 | neural_networks, backpropagation | 100 | no | Implement a 2-layer network with backpropagation. |
| c601_hw6 | 10-601 | Homework 6: Learning Theory and Ethics | d+10 23:59 | pac_learning, societal_impacts | 60 | no | Written. |
| c601_exam2 | 10-601 | Exam 2 (in person) | d+12 19:00 | optimization_sgd, logistic_regression, neural_networks, backpropagation, regularization | 0 | no | Covers lectures 8-17. |
| c605_hw4 | 10-605 | HW 4: LoRA | d-3 23:59 | lora, transformers_lms | 100 | yes | Programming + written. |
| c605_hw5 | 10-605 | HW 5: GPT-2 Training | d+11 23:59 | transformers_lms, parallel_training, gpu_optimization | 100 | no | Train a small GPT-2 efficiently. |
| c605_mini | 10-605 | Miniproject | d+23 23:59 | distributed_learning, rag | 150 | no | Structured miniproject. |
| c831_hw2 | 16-831 | HW2 | d-4 23:59 | imitation_learning, value_policy_iteration, q_learning | 100 | yes | Submitted. |
| c831_hw3 | 16-831 | HW3: Policy gradients and actor-critic | d+5 23:59 | policy_gradients, actor_critic | 100 | no | Derive and implement REINFORCE with a baseline. |
| c831_proposal | 16-831 | Project proposal: language-conditioned manipulation | d+11 23:59 | foundation_models_robotics, imitation_learning | 50 | no | One page: a robot arm that follows natural-language instructions. |
"""

PIAZZA_PACK = f"""<!-- {MARK} -->
# Piazza export

## Piazza posts

### HW5: clarification on backprop through the softmax layer
- id: p601_1
- course: 10-601
- posted: d-1 16:10
- author: instructor
- type: announcement
- concepts: backpropagation

When computing gradients for HW5, combine softmax and cross-entropy: the gradient with respect to the logits is (y_hat - y).

### Found a great paper on vision-language-action models (RT-2)
- id: p831_2
- course: 16-831
- posted: d-1 19:45
- author: student
- type: note
- concepts: foundation_models_robotics
- url: https://arxiv.org/abs/2307.15818

For anyone thinking about project ideas: RT-2 shows how a vision-language model can output robot actions directly. Really relevant to the project proposal.

### Why do my gradients explode in HW5?
- id: p601_2
- course: 10-601
- posted: d-1 22:40
- author: student
- type: question
- concepts: backpropagation, neural_networks

My loss becomes NaN after a few epochs. Is this an initialization problem?

### HW 5: memory tips for GPT-2 training
- id: p605_1
- course: 10-605
- posted: d-1 11:30
- author: instructor
- type: announcement
- concepts: gpu_optimization, kv_caching

If you run out of GPU memory in HW 5, try gradient accumulation and a smaller context length first.

### HW3 released: policy gradient written problems
- id: p831_1
- course: 16-831
- posted: d-2 09:00
- author: instructor
- type: announcement
- concepts: policy_gradients, actor_critic

HW3 is out. Start early on the REINFORCE derivation; office hours are on the course calendar.
"""


ED_PACK = f"""<!-- {MARK} -->
# Ed Discussion export

## Ed Discussion posts

### HW 5: office hours moved to Thursday this week
- id: ed605_1
- course: 10-605
- posted: d-1 09:15
- author: instructor
- type: announcement
- concepts: transformers_lms, parallel_training

Thursday's office hours cover GPT-2 training setups. Bring your profiler output if you are running out of memory.

### All-reduce vs. a parameter server: why is there no central node?
- id: ed605_2
- course: 10-605
- posted: d-2 20:10
- author: student
- type: question
- concepts: distributed_learning

From lecture: all-reduce leaves the summed gradient on every worker. Does that mean no single machine is a bottleneck? An instructor-endorsed answer explains the ring version step by step.

### Tip: measuring GPU memory per layer for HW 5
- id: ed605_3
- course: 10-605
- posted: d-1 23:30
- author: student
- type: note
- concepts: gpu_optimization

torch.cuda.max_memory_allocated() after each block made it obvious the attention activations were the problem.
"""


def manifest_entries() -> list[dict]:
    return [
        {"step": 1, "name": "01_10601_course_overview.pdf", "kind": "course_overview",
         "title": "10-601 Intro to ML — course overview",
         "description": "Course code plus 19 lecture-topic concepts from the public 10-601 schedule.",
         "what_to_notice": "MentorIA learns its first course: the knowledge bar counts concepts, and Student Model lists them (no estimates yet)."},
        {"step": 2, "name": "02_16831_course_overview.pdf", "kind": "course_overview",
         "title": "16-831 Intro to Robot Learning — course overview",
         "description": "16 concepts from the public 16-831 lecture list, incl. Foundation Models in Robotics.",
         "what_to_notice": "A second course appears; the graph links 10-601 Transformers to 16-831 Foundation Models."},
        {"step": 3, "name": "03_10605_course_overview.pdf", "kind": "course_overview",
         "title": "10-605 ML with Large Datasets — course overview",
         "description": "13 concepts from the public 10-605 schedule plus 6 concepts it shares with 10-601.",
         "what_to_notice": "Shared concepts (e.g. Backpropagation) now belong to both ML courses — one estimate, shared evidence."},
        {"step": 4, "name": "04_canvas_assignments.md", "kind": "source_pack", "title": "Canvas assignments export",
         "description": "This week's homework, an exam and a project proposal across both courses.",
         "what_to_notice": "Canvas card fills; 'Due soon' and 'No graded evidence for…' insights appear."},
        {"step": 5, "name": "05_my_calendar.ics", "kind": "calendar", "title": "My calendar (next 7 days)",
         "description": "Lectures, office hours, job shifts and a coffee chat with a startup founder.",
         "what_to_notice": "Calendar card and free study windows appear; weekly plans can now propose real times."},
        {"step": 6, "name": "06_10601_quiz2_graded.pdf", "kind": "graded_assessment", "title": "10-601 Quiz 2 (graded)",
         "description": "7 graded questions on logistic regression, neural nets and backprop; one has partial credit.",
         "what_to_notice": "Mastery estimates appear: Backpropagation drops to ~0.12; Q7 (partial credit) is held for review."},
        {"step": 7, "name": "07_16831_hw2_graded.pdf", "kind": "graded_assessment", "title": "16-831 HW2 written problems (graded)",
         "description": "6 graded questions on imitation learning, value iteration, Q-learning and policy gradients.",
         "what_to_notice": "Policy Gradients shows as a gap; 'What should I focus on this week?' now cites both courses."},
        {"step": 8, "name": "08_10605_lecture_quizzes_graded.pdf", "kind": "graded_assessment",
         "title": "10-605 lecture quizzes (graded)",
         "description": "6 graded lecture-quiz questions incl. autodiff, LSH, sketches and all-reduce.",
         "what_to_notice": "The autodiff miss lowers Backpropagation further — evidence from 10-601 and 10-605 combines."},
        {"step": 9, "name": "09_career_goals_statement.pdf", "kind": "personal_document", "title": "My career goals statement",
         "description": "Your own writing: you want to work at a startup building robots that understand language.",
         "what_to_notice": "A goal card appears on the dashboard; the goal links to Foundation Models in Robotics in the graph."},
        {"step": 10, "name": "10_email_to_advisor.eml", "kind": "email", "title": "Email you sent to your advisor",
         "description": "You tell your advisor you'd like to join a startup that makes robots understand language.",
         "what_to_notice": "The same goal is reinforced — now 'stated in 2 sources' (not duplicated)."},
        {"step": 11, "name": "11_email_vla_seminar.eml", "kind": "email", "title": "Seminar: robots that follow language instructions",
         "description": "A dated robotics seminar on vision-language-action models.",
         "what_to_notice": "Ranked as a top opportunity because it matches your goal; an approval-gated calendar proposal appears."},
        {"step": 12, "name": "12_email_startup_mixer.eml", "kind": "email", "title": "Robotics & AI startup mixer",
         "description": "Founders hiring interns and new grads, incl. language-driven robots.",
         "what_to_notice": "Matches the 'startup' part of your goal."},
        {"step": 13, "name": "13_email_rl_reading_group.eml", "kind": "email", "title": "RL reading group: policy gradients",
         "description": "A reading group on a topic where your graded work shows a gap.",
         "what_to_notice": "Relevant because of a knowledge gap, not your goal — the reasons say so."},
        {"step": 14, "name": "14_email_quant_club.eml", "kind": "email", "title": "Quant finance club kickoff",
         "description": "An unrelated announcement.",
         "what_to_notice": "Ranked low and skipped in chat — MentorIA filters noise."},
        {"step": 15, "name": "15_piazza_posts.md", "kind": "source_pack", "title": "Piazza posts export",
         "description": "Instructor clarifications for 10-601 HW5 and 16-831 HW3, plus a student question.",
         "what_to_notice": "Piazza card fills; instructor posts are badged. Questions never lower your mastery."},
        {"step": 17, "name": "17_ed_discussion_posts.md", "kind": "source_pack", "title": "Ed Discussion posts export (10-605)",
         "description": "An instructor note and two classmate posts from the 10-605 forum.",
         "what_to_notice": "They appear under Relevant discussions from course forums, tagged Ed."},
        {"step": 18, "name": "18_email_10601_exam2_logistics.eml", "kind": "email", "title": "[10-601] Exam 2 logistics",
         "description": "A course-staff email.",
         "what_to_notice": "Filed under course discussions (tagged Email), not opportunities."},
        {"step": 16, "name": "16_10601_practice_ungraded.pdf", "kind": "study_material",
         "title": "10-601 practice problems (ungraded)",
         "description": "A question sheet without answers or grades.",
         "what_to_notice": "Indexed as study material only — no mastery numbers change."},
    ]


def generate(out: Path = OUT) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    today = datetime.now(settings.tz).date()
    student = f"{settings.student_name} <{settings.student_email}>"
    course_overview(ML, out / "01_10601_course_overview.pdf")
    course_overview(RL, out / "02_16831_course_overview.pdf")
    course_overview(LD, out / "03_10605_course_overview.pdf")
    (out / "04_canvas_assignments.md").write_text(CANVAS_PACK)
    ics(out / "05_my_calendar.ics", today)
    graded(out / "06_10601_quiz2_graded.pdf", "10-601 Quiz 2 (graded)", ML, today - timedelta(days=2), "7/14", [
        [(1, "Logistic Regression", "What does the sigmoid output represent in binary logistic regression?",
          "P(y = 1 | x)", "Correct", "2/2", ""),
         (2, "Logistic Regression", "Give the gradient of the negative log-likelihood with respect to w.",
          "sum_i (y_i - sigmoid(w.x_i)) x_i", "Incorrect", "0/2", "Sign error: it is sum_i (sigmoid(w.x_i) - y_i) x_i."),
         (3, "Neural Networks", "Why do we need nonlinear activation functions?",
          "Otherwise the network is just a linear model", "Correct", "2/2", "")],
        [(4, "Backpropagation", "In a 2-layer network, which cached forward values are needed to compute dL/dW1?",
          "Only the output y_hat", "Incorrect", "0/2", "You also need the hidden activations and pre-activations."),
         (5, "Backpropagation", "Apply the chain rule: write dL/dz1 for z1 = W1 x, h = sigmoid(z1).",
          "dL/dh * W1", "Incorrect", "0/2", "Missing the sigmoid derivative h(1-h); W1 multiplies on the wrong side."),
         (6, "Regularization", "What does L2 regularization do to large weights?",
          "Penalizes them, shrinking weights toward zero", "Correct", "2/2", ""),
         (7, "Optimization & SGD", "Why might SGD with a constant learning rate fail to converge exactly?",
          "Because the gradients are noisy", None, "1/2", "Partial credit: mention the need for a decaying step size.")],
    ])
    graded(out / "07_16831_hw2_graded.pdf", "16-831 HW2 written problems (graded)", RL, today - timedelta(days=1), "8/12", [
        [(1, "Imitation Learning", "Why does behavior cloning suffer from compounding errors?",
          "Small mistakes lead to unseen states", "Correct", "2/2", ""),
         (2, "Imitation Learning", "How does DAgger address distribution shift?",
          "It queries the expert on states visited by the learner", "Correct", "2/2", ""),
         (3, "Value & Policy Iteration", "When does value iteration converge?",
          "When the Bellman update stops changing V (contraction)", "Correct", "2/2", "")],
        [(4, "Policy Gradients", "Write the REINFORCE gradient estimator.",
          "grad = E[ grad log pi(a|s) ]", "Incorrect", "0/2", "Missing the return (reward-to-go) weighting."),
         (5, "Policy Gradients", "Why does subtracting a baseline not bias the policy gradient?",
          "Because it lowers variance", "Incorrect", "0/2", "That's why we use it; unbiasedness is because E[grad log pi * b] = 0."),
         (6, "Q-Learning", "Why is Q-learning off-policy?",
          "Its target uses max over actions, not the behavior policy's action", "Correct", "2/2", "")],
    ])
    graded(out / "08_10605_lecture_quizzes_graded.pdf", "10-605 lecture quizzes (graded)", LD, today - timedelta(days=1), "6/12", [
        [(1, "Backpropagation", "In reverse-mode autodiff, why does one backward pass give the gradient for every parameter?",
          "Because each parameter gets its own backward pass", "Incorrect", "0/2",
          "Reverse mode propagates the adjoint of the single scalar loss through the graph once."),
         (2, "Locality-Sensitive Hashing", "What does MinHash estimate between two sets?",
          "Their Jaccard similarity", "Correct", "2/2", ""),
         (3, "Bloom Filters & Count-Min Sketch", "Can a Bloom filter return a false negative?",
          "Yes, if the filter is full", "Incorrect", "0/2", "No: only false positives are possible.")],
        [(4, "Transformers", "Why does self-attention cost O(n^2) in sequence length?",
          "Every token attends to every other token", "Correct", "2/2", ""),
         (5, "Distributed Learning & All-Reduce", "What does all-reduce compute in data-parallel SGD?",
          "It sends all gradients to one parameter server", "Incorrect", "0/2",
          "All-reduce sums gradients across workers and leaves the result on every worker, with no central server."),
         (6, "KV Caching for LLMs", "What does the KV cache avoid recomputing during generation?",
          "Keys and values for previous tokens", "Correct", "2/2", "")],
    ])
    personal_statement(out / "09_career_goals_statement.pdf")
    now = datetime.now(settings.tz)
    write_email(out / "10_email_to_advisor.eml", student, "Prof. Lee <advisor@example.edu>",
                "Advice on projects for a robotics + language career",
                "Hi Professor Lee,\n\nThanks for meeting last week. I've been thinking more about what I want after "
                "graduation. I'd like to join a startup that makes robots understand language, ideally working on "
                "vision-language-action models.\n\nCould we talk about which project in 16-831 would help most?\n\n"
                f"Thanks,\n{settings.student_name}\n", now - timedelta(hours=20))
    seminar = _at(today, 4, 17)
    write_email(out / "11_email_vla_seminar.eml", "Robotics Seminar <robotics-seminar@example.edu>", settings.student_email,
                "Robotics Seminar: Teaching Robots to Follow Language Instructions with Vision-Language-Action Models",
                "Robotics Seminar Series\n"
                "Speaker: Dr. Maya Okafor (Example Robotics Lab)\n"
                "Title: Teaching Robots to Follow Language Instructions with Vision-Language-Action Models\n"
                f"When: {_human(seminar)}\n"
                "Where: Robotics Seminar Room\n"
                "Zoom: https://example.edu/robotics-seminar/vla\n\n"
                "Abstract: How can a robot turn \"put the red cup on the shelf\" into actions? This talk covers "
                "vision-language-action (VLA) models, language-conditioned manipulation, and lessons from deploying "
                "them on real robot arms.\n", now - timedelta(hours=30))
    mixer = _at(today, 6, 18)
    write_email(out / "12_email_startup_mixer.eml", "Entrepreneurship Center <startups@example.edu>", settings.student_email,
                "Robotics & AI Startup Mixer: founders hiring interns and new grads",
                "Meet founders of early-stage robotics and AI startups, including teams building home robots that "
                "understand natural language instructions. Several are hiring interns and new grads.\n"
                f"When: {_human(mixer)}\n"
                "Where: Innovation Hub\n", now - timedelta(hours=26))
    reading = _at(today, 2, 12)
    write_email(out / "13_email_rl_reading_group.eml", "RL Reading Group <rl-reading@example.edu>", settings.student_email,
                "RL Reading Group: policy gradient methods, from REINFORCE to PPO",
                "This week we read the REINFORCE paper and discuss variance reduction with baselines in policy gradient "
                "methods.\n"
                f"When: {_human(reading)}\n"
                "Where: Robotics Lounge\n", now - timedelta(hours=40))
    quant = _at(today, 5, 19)
    write_email(out / "14_email_quant_club.eml", "Quant Finance Club <quant@example.edu>", settings.student_email,
                "Quant Finance Club: trading competition kickoff",
                "Join our trading competition kickoff. Pizza provided.\n"
                f"When: {_human(quant)}\n"
                "Where: Business School Atrium\n", now - timedelta(hours=50))
    (out / "15_piazza_posts.md").write_text(PIAZZA_PACK)
    practice_sheet(out / "16_10601_practice_ungraded.pdf")
    (out / "17_ed_discussion_posts.md").write_text(ED_PACK)
    exam = _at(today, 12, 19)
    write_email(out / "18_email_10601_exam2_logistics.eml", "10-601 Course Staff <10601-staff@example.edu>", settings.student_email,
                "[10-601] Exam 2 logistics and practice problems",
                f"Exam 2 is on {_human(exam)} and covers lectures 8-17: optimization, logistic regression, regularization, "
                "neural networks and backpropagation. Practice problems and solutions are posted on the course website.\n",
                now - timedelta(hours=6))
    manifest = {"generated_on": today.isoformat(), "student_name": settings.student_name,
                "student_email": settings.student_email, "assets": manifest_entries()}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return out
