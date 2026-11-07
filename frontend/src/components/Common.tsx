import { Fragment, useState, type ReactNode } from "react";
import type { ConnectorStatus, EvidenceRef } from "../api/types";
import { fmtDateTime, providerLabel } from "../lib/format";

export function StatusDot({ status }: { status: ConnectorStatus }) {
  return (
    <span
      className={`dot dot-${status.state}`}
      title={`${providerLabel(status.provider)}: ${status.state} (${status.mode}) — ${status.detail}`}
    />
  );
}

export function StatusBadge({ status }: { status: ConnectorStatus | undefined }) {
  if (!status) return null;
  return (
    <span className={`badge badge-${status.state}`} title={status.detail}>
      <StatusDot status={status} />
      {status.state.replace("_", " ")}
      {status.mode !== "none" && <span className="badge-mode"> · {status.mode === "import" ? "from files" : status.mode}</span>}
      {status.verified_live && <span className="badge-mode"> · verified</span>}
    </span>
  );
}

export function DemoLabel({ show = true }: { show?: boolean }) {
  if (!show) return null;
  return <span className="demo-label">Demo data</span>;
}

export function Card({
  title,
  status,
  demo,
  actions,
  children,
  className,
}: {
  title: ReactNode;
  status?: ConnectorStatus;
  demo?: boolean;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`card ${className ?? ""}`}>
      <header className="card-head">
        <h2>{title}</h2>
        <div className="card-head-right">
          <DemoLabel show={!!demo} />
          <StatusBadge status={status} />
          {actions}
        </div>
      </header>
      {status && (status.state === "failed" || status.state === "needs_auth") && (
        <div className={`card-error ${status.state}`}>
          {status.state === "failed" ? "Sync failed: " : "Needs authorization: "}
          {status.detail}
        </div>
      )}
      <div className="card-body">{children}</div>
      {status?.last_synced_at && <footer className="card-foot">Last sync {fmtDateTime(status.last_synced_at)}</footer>}
    </section>
  );
}

export function EvidenceChips({ evidence }: { evidence: EvidenceRef[] }) {
  if (!evidence || evidence.length === 0) return null;
  return (
    <div className="chips">
      {evidence.map((e, i) => {
        const inner = (
          <>
            <span className="chip-provider">{providerLabel(e.provider)}</span> {e.label}
            {e.is_fixture && <span className="chip-demo">Demo</span>}
          </>
        );
        return e.url ? (
          <a key={`${e.id}-${i}`} className="chip" href={e.url} target="_blank" rel="noreferrer">
            {inner}
          </a>
        ) : (
          <span key={`${e.id}-${i}`} className="chip">
            {inner}
          </span>
        );
      })}
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="empty">{children}</p>;
}

export function Bar({ value, color }: { value: number | null | undefined; color?: string }) {
  const v = value === null || value === undefined ? 0 : Math.max(0, Math.min(1, value));
  return (
    <span className="bar">
      <span className="bar-fill" style={{ width: `${v * 100}%`, background: color ?? "var(--accent)" }} />
    </span>
  );
}

function renderInline(text: string): ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((p, i) =>
    p.startsWith("**") && p.endsWith("**") && p.length > 4 ? <strong key={i}>{p.slice(2, -2)}</strong> : <Fragment key={i}>{p}</Fragment>,
  );
}

/** Markdown-lite: paragraphs, "- " bullets, **bold**. Never renders raw HTML. */
export function MarkdownLite({ text }: { text: string }) {
  const blocks: ReactNode[] = [];
  const lines = (text ?? "").split("\n");
  let list: string[] = [];
  let para: string[] = [];
  const flushList = () => {
    if (list.length) {
      blocks.push(
        <ul key={`l${blocks.length}`}>
          {list.map((l, i) => (
            <li key={i}>{renderInline(l)}</li>
          ))}
        </ul>,
      );
      list = [];
    }
  };
  const flushPara = () => {
    if (para.length) {
      blocks.push(<p key={`p${blocks.length}`}>{renderInline(para.join(" "))}</p>);
      para = [];
    }
  };
  for (const raw of lines) {
    const line = raw.trimEnd();
    const m = line.match(/^\s*[-*]\s+(.*)$/);
    if (m) {
      flushPara();
      list.push(m[1]);
    } else if (line.trim() === "") {
      flushPara();
      flushList();
    } else {
      flushList();
      para.push(line.trim());
    }
  }
  flushPara();
  flushList();
  return <div className="md">{blocks}</div>;
}

/** Compact dashboard block: icon + short title + status dot (details in tooltip) + one Demo pill. */
export function Block({
  icon,
  title,
  status,
  demo,
  actions,
  children,
  className,
}: {
  icon: string;
  title: string;
  status?: ConnectorStatus;
  demo?: boolean;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`card block ${className ?? ""}`}>
      <header className="block-head">
        <span className="block-icon" aria-hidden>
          {icon}
        </span>
        <h2>{title}</h2>
        {status && <StatusDot status={status} />}
        {demo && <span className="pill pill-demo">Demo</span>}
        <span className="block-actions">{actions}</span>
      </header>
      {status?.state === "failed" && (
        <div className="block-error" title={status.detail}>
          Sync failed
        </div>
      )}
      {children}
    </section>
  );
}

/** Shows the first `limit` items with a "+N more" toggle. */
export function MoreList<T>({
  items,
  limit = 4,
  render,
  className = "items",
}: {
  items: T[];
  limit?: number;
  render: (item: T, i: number) => ReactNode;
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  const shown = open ? items : items.slice(0, limit);
  return (
    <>
      <ul className={className}>{shown.map((it, i) => render(it, i))}</ul>
      {items.length > limit && (
        <button className="link-btn more-btn" onClick={() => setOpen((o) => !o)}>
          {open ? "Show less" : `+${items.length - limit} more`}
        </button>
      )}
    </>
  );
}

/** One-line item: title + muted meta line, optional right-side element. */
export function Item({
  title,
  meta,
  side,
  tip,
  done,
  children,
}: {
  title: ReactNode;
  meta?: ReactNode;
  side?: ReactNode;
  tip?: string;
  done?: boolean;
  children?: ReactNode;
}) {
  return (
    <li className={`item ${done ? "done" : ""}`} title={tip}>
      <div className="item-main">
        <div className="item-title">{title}</div>
        {meta && <div className="item-meta">{meta}</div>}
        {children}
      </div>
      {side && <div className="item-side">{side}</div>}
    </li>
  );
}

/** Small "why?" toggle that reveals a short list of reasons. */
export function Why({ reasons, label = "why?" }: { reasons: string[]; label?: string }) {
  const [open, setOpen] = useState(false);
  if (!reasons.length) return null;
  return (
    <>
      <button className="link-btn why-btn" onClick={() => setOpen((o) => !o)}>
        {open ? "hide" : label}
      </button>
      {open && (
        <ul className="why-list">
          {reasons.map((r, i) => (
            <li key={i}>{r}</li>
          ))}
        </ul>
      )}
    </>
  );
}
