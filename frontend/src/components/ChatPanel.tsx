import { useEffect, useRef, useState, type FormEvent } from "react";
import { api, DEFAULT_STUDENT } from "../api/client";
import type { ChatMessage, ChatResponse } from "../api/types";
import { ApprovalCard } from "./ApprovalCard";
import { EvidenceChips, MarkdownLite } from "./Common";

type Mode = "ask" | "tell";

/** Ask chips send immediately. */
const ASK_CHIPS: { label: string; send: string }[] = [
  { label: "ML topics I'm struggling with?", send: "What ML topics am I struggling with?" },
  { label: "Focus this week?", send: "What should I focus on this week?" },
  { label: "Classes to take next?", send: "What classes should I take next?" },
  { label: "Events to attend?", send: "Any events I should attend?" },
];

/** About-me chips prefill the input so the student finishes the sentence. */
const TELL_PREFILLS = [
  "My career goal is to ",
  "I'm interested in ",
  "I prefer studying ",
  "I'm confident about ",
  "I'm not confident about ",
  "I'm feeling ",
];
const TELL_EXAMPLE = "I want a job at a startup that makes robots understand language";

interface Turn {
  role: "user" | "assistant";
  content: string;
  response?: ChatResponse;
  error?: string;
}

// Each tab keeps its own conversation across page navigation within the session.
const saved: Record<Mode, Turn[]> = { ask: [], tell: [] };
let savedMode: Mode = "ask";

export function ChatPanel({ tz, onMemoryChanged }: { tz: string; onMemoryChanged?: () => void }) {
  const [mode, setMode] = useState<Mode>(savedMode);
  const [turns, setTurns] = useState<Record<Mode, Turn[]>>({ ...saved });
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    saved.ask = turns.ask;
    saved.tell = turns.tell;
  }, [turns]);
  useEffect(() => {
    savedMode = mode;
  }, [mode]);
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns, busy, mode]);

  const current = turns[mode];

  async function send(text: string) {
    const message = text.trim();
    if (!message || busy) return;
    const m = mode;
    const history: ChatMessage[] = turns[m].filter((t) => !t.error).map((t) => ({ role: t.role, content: t.content }));
    setTurns((all) => ({ ...all, [m]: [...all[m], { role: "user", content: message }] }));
    setInput("");
    setBusy(true);
    try {
      const res = await api.chat({ message, student_id: DEFAULT_STUDENT, history, mode: m });
      setTurns((all) => ({ ...all, [m]: [...all[m], { role: "assistant", content: res.answer, response: res }] }));
      if (m === "tell" || res.memory_updates.length > 0 || res.proposed_recommendations.length > 0) onMemoryChanged?.();
    } catch (e) {
      setTurns((all) => ({ ...all, [m]: [...all[m], { role: "assistant", content: "", error: (e as Error).message }] }));
    } finally {
      setBusy(false);
    }
  }

  function prefill(text: string) {
    setInput(text);
    requestAnimationFrame(() => {
      const el = inputRef.current;
      if (el) {
        el.focus();
        el.setSelectionRange(text.length, text.length);
      }
    });
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    void send(input);
  }

  return (
    <section className="card chat">
      <div className="chat-tabs" role="tablist">
        <button role="tab" aria-selected={mode === "ask"} className={`chat-tab ${mode === "ask" ? "active" : ""}`} onClick={() => setMode("ask")}>
          Ask
        </button>
        <button role="tab" aria-selected={mode === "tell"} className={`chat-tab ${mode === "tell" ? "active" : ""}`} onClick={() => setMode("tell")}>
          About me
        </button>
      </div>
      <div className="chat-log">
        {current.length === 0 && (
          <p className="empty">{mode === "ask" ? "Ask about your courses, deadlines or opportunities." : "Tell MentorIA your goals, interests and how you study."}</p>
        )}
        {current.map((t, i) => (
          <div key={i} className={`msg msg-${t.role}`}>
            {t.role === "user" ? (
              <div className="bubble user">{t.content}</div>
            ) : t.error ? (
              <div className="bubble assistant error-text">Error: {t.error}</div>
            ) : mode === "tell" ? (
              <TellTurn res={t.response!} />
            ) : (
              <AssistantTurn res={t.response!} tz={tz} onChanged={onMemoryChanged} />
            )}
          </div>
        ))}
        {busy && <div className="bubble assistant thinking">Thinking…</div>}
        <div ref={endRef} />
      </div>
      <div className="suggestions">
        {mode === "ask" ? (
          ASK_CHIPS.map((c) => (
            <button key={c.label} className="suggestion" disabled={busy} onClick={() => void send(c.send)}>
              {c.label}
            </button>
          ))
        ) : (
          <>
            {TELL_PREFILLS.map((p) => (
              <button key={p} className="suggestion prefill" disabled={busy} onClick={() => prefill(p)}>
                {p.trim()}…
              </button>
            ))}
            <button className="suggestion example" disabled={busy} onClick={() => void send(TELL_EXAMPLE)} title="Sends this example">
              “{TELL_EXAMPLE}”
            </button>
          </>
        )}
      </div>
      <form className="chat-input" onSubmit={onSubmit}>
        <input
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={mode === "ask" ? "Ask MentorIA…" : "Tell MentorIA about your goals, interests, how you study…"}
          disabled={busy}
          aria-label={mode === "ask" ? "Ask MentorIA" : "Tell MentorIA about yourself"}
        />
        <button className="btn primary" type="submit" disabled={busy || !input.trim()}>
          Send
        </button>
      </form>
    </section>
  );
}

function TellTurn({ res }: { res: ChatResponse }) {
  return (
    <div className="bubble assistant">
      {res.memory_updates.length > 0 && (
        <ul className="saved-list">
          {res.memory_updates.map((m, i) => (
            <li key={i}>✓ {m}</li>
          ))}
        </ul>
      )}
      <MarkdownLite text={res.answer} />
      {res.sources.length > 0 && <EvidenceChips evidence={res.sources} />}
    </div>
  );
}

function AssistantTurn({ res, tz, onChanged }: { res: ChatResponse; tz: string; onChanged?: () => void }) {
  return (
    <div className="bubble assistant">
      <MarkdownLite text={res.answer} />
      {res.memory_updates.length > 0 && (
        <ul className="saved-list">
          {res.memory_updates.map((m, i) => (
            <li key={i}>✓ {m}</li>
          ))}
        </ul>
      )}
      {res.sources.length > 0 && <EvidenceChips evidence={res.sources} />}
      {res.uncertainties.length > 0 && (
        <details className="caveats">
          <summary>Caveats ({res.uncertainties.length})</summary>
          <ul>
            {res.uncertainties.map((u, i) => (
              <li key={i}>{u}</li>
            ))}
          </ul>
        </details>
      )}
      {res.proposed_recommendations.map((r) => (
        <ApprovalCard key={r.id} rec={r} tz={tz} onChanged={onChanged} compact />
      ))}
    </div>
  );
}
