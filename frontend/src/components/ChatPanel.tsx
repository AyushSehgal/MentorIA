import { useEffect, useRef, useState, type FormEvent } from "react";
import { api, DEFAULT_STUDENT } from "../api/client";
import type { ChatMessage, ChatResponse } from "../api/types";
import { ApprovalCard } from "./ApprovalCard";
import { EvidenceChips, MarkdownLite } from "./Common";

const SUGGESTIONS = [
  "What systems topics am I struggling with?",
  "What should I focus on this week?",
  "What classes should I take next?",
  "Any research talks I should attend?",
];

interface Turn {
  role: "user" | "assistant";
  content: string;
  response?: ChatResponse;
  error?: string;
}

// Persist the conversation across page navigation within the session.
let savedTurns: Turn[] = [];

export function ChatPanel({ tz, onMemoryChanged }: { tz: string; onMemoryChanged?: () => void }) {
  const [turns, setTurns] = useState<Turn[]>(savedTurns);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    savedTurns = turns;
  }, [turns]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns, busy]);

  async function send(text: string) {
    const message = text.trim();
    if (!message || busy) return;
    const history: ChatMessage[] = turns
      .filter((t) => !t.error)
      .map((t) => ({ role: t.role, content: t.content }));
    setTurns((t) => [...t, { role: "user", content: message }]);
    setInput("");
    setBusy(true);
    try {
      const res = await api.chat({ message, student_id: DEFAULT_STUDENT, history });
      setTurns((t) => [...t, { role: "assistant", content: res.answer, response: res }]);
      if (res.memory_updates.length > 0 || res.proposed_recommendations.length > 0) onMemoryChanged?.();
    } catch (e) {
      setTurns((t) => [...t, { role: "assistant", content: "", error: (e as Error).message }]);
    } finally {
      setBusy(false);
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    void send(input);
  }

  return (
    <section className="card chat">
      <header className="card-head">
        <h2>Ask NOVA</h2>
        <span className="muted small">Cross-source, evidence-backed</span>
      </header>
      <div className="chat-log">
        {turns.length === 0 && (
          <p className="empty">
            Ask about your courses, deadlines, knowledge gaps, or opportunities. You can also tell NOVA things like
            “I’m confident with virtual memory” or “My goal is embodied AI research” to update your student model.
          </p>
        )}
        {turns.map((t, i) => (
          <div key={i} className={`msg msg-${t.role}`}>
            {t.role === "user" ? (
              <div className="bubble user">{t.content}</div>
            ) : t.error ? (
              <div className="bubble assistant error-text">Error: {t.error}</div>
            ) : (
              <AssistantTurn res={t.response!} tz={tz} onChanged={onMemoryChanged} />
            )}
          </div>
        ))}
        {busy && <div className="bubble assistant thinking">NOVA is gathering evidence…</div>}
        <div ref={endRef} />
      </div>
      <div className="suggestions">
        {SUGGESTIONS.map((s) => (
          <button key={s} className="suggestion" disabled={busy} onClick={() => void send(s)}>
            {s}
          </button>
        ))}
      </div>
      <form className="chat-input" onSubmit={onSubmit}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask NOVA anything about your semester…"
          disabled={busy}
          aria-label="Chat message"
        />
        <button className="btn primary" type="submit" disabled={busy || !input.trim()}>
          Send
        </button>
      </form>
    </section>
  );
}

function AssistantTurn({ res, tz, onChanged }: { res: ChatResponse; tz: string; onChanged?: () => void }) {
  return (
    <div className="bubble assistant">
      <MarkdownLite text={res.answer} />
      {res.memory_updates.length > 0 && (
        <div className="memory-note">
          <strong>Memory updated:</strong>
          <ul>
            {res.memory_updates.map((m, i) => (
              <li key={i}>{m}</li>
            ))}
          </ul>
        </div>
      )}
      {res.sources.length > 0 && (
        <div className="chat-sources">
          <span className="muted small">Sources</span>
          <EvidenceChips evidence={res.sources} />
        </div>
      )}
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
      <div className="chat-foot">
        intent: {res.intent} · trace: {res.trace.join(" → ") || "—"} ·{" "}
        {res.llm_used ? `worded by ${res.llm_provider}` : "grounded draft (no LLM)"}
        {res.llm_note && <div className="muted">{res.llm_note}</div>}
      </div>
    </div>
  );
}
