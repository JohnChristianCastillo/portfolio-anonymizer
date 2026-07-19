import { useEffect, useState } from "react";

import { anonymize, fetchConfigs } from "../lib/api";
import type { AnonymizeResult, DetectorConfig, Entity } from "../lib/types";

const SAMPLE =
  "Maria Lopez is a data engineer at Contoso Ltd in Antwerp. " +
  "Reach her at maria.lopez@contoso.example or +32 470 12 34 56, " +
  "and see www.contoso.example for details.";

type Segment = { text: string; label: string | null };

/** Split the original text into plain and entity segments, in order. */
function segments(text: string, entities: Entity[]): Segment[] {
  const ordered = [...entities].sort((a, b) => a.start - b.start);
  const out: Segment[] = [];
  let cursor = 0;
  for (const entity of ordered) {
    if (entity.start > cursor) {
      out.push({ text: text.slice(cursor, entity.start), label: null });
    }
    out.push({ text: text.slice(entity.start, entity.end), label: entity.label });
    cursor = entity.end;
  }
  if (cursor < text.length) out.push({ text: text.slice(cursor), label: null });
  return out;
}

/** Render the anonymized output with each <LABEL> placeholder as a chip. */
function renderAnonymized(text: string) {
  const parts = text.split(/(<[A-Z_]+>)/g);
  return parts.map((part, index) =>
    /^<[A-Z_]+>$/.test(part) ? (
      <mark key={index} className="tag tag--placeholder">
        {part.slice(1, -1)}
      </mark>
    ) : (
      <span key={index}>{part}</span>
    ),
  );
}

export function Demo({ admitted }: { admitted: boolean }) {
  const [text, setText] = useState(SAMPLE);
  const [configs, setConfigs] = useState<DetectorConfig[]>([]);
  const [config, setConfig] = useState("");
  const [result, setResult] = useState<AnonymizeResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!admitted) return;
    fetchConfigs()
      .then((list) => {
        setConfigs(list);
        const preferred = list.find((c) => c.default) ?? list[0];
        if (preferred) setConfig(preferred.key);
      })
      .catch((e: Error) => setError(e.message));
  }, [admitted]);

  async function run() {
    setBusy(true);
    setError(null);
    try {
      setResult(await anonymize(text, config));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const counts = result ? Object.entries(result.entity_counts) : [];

  return (
    <section className="card" id="try">
      <header className="card__head">
        <h2>Try it</h2>
        <p className="muted">
          Paste any text. Nothing is stored: the text is processed in memory and
          returned.
        </p>
      </header>

      <textarea
        className="input"
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={5}
        spellCheck={false}
        aria-label="Text to anonymize"
      />

      <div className="controls">
        <label className="field">
          <span className="field__label">Detectors</span>
          <select
            value={config}
            onChange={(e) => setConfig(e.target.value)}
            disabled={!admitted || configs.length === 0}
          >
            {configs.map((c) => (
              <option key={c.key} value={c.key}>
                {c.label}
              </option>
            ))}
          </select>
        </label>

        <button
          className="button"
          onClick={run}
          disabled={!admitted || busy || !config || text.trim().length === 0}
        >
          {busy ? "Analyzing..." : "Anonymize"}
        </button>
      </div>

      {error && <p className="error">{error}</p>}

      {result && (
        <>
          <div className="split">
            <div className="pane">
              <h3 className="pane__title">Input, entities detected</h3>
              <p className="pane__body">
                {segments(result.original ?? text, result.entities).map((seg, i) =>
                  seg.label ? (
                    <mark key={i} className="tag tag--found" data-label={seg.label}>
                      {seg.text}
                      <span className="tag__label">{seg.label}</span>
                    </mark>
                  ) : (
                    <span key={i}>{seg.text}</span>
                  ),
                )}
              </p>
            </div>

            <div className="pane">
              <h3 className="pane__title">Output, anonymized</h3>
              <p className="pane__body">{renderAnonymized(result.anonymized)}</p>
            </div>
          </div>

          <div className="counts">
            {counts.length === 0 ? (
              <span className="muted">No entities detected.</span>
            ) : (
              counts.map(([label, n]) => (
                <span key={label} className="chip">
                  {label}
                  <b>{n}</b>
                </span>
              ))
            )}
          </div>
        </>
      )}
    </section>
  );
}
