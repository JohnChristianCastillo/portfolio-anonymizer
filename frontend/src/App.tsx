import { useEffect } from "react";

import { Demo } from "./components/Demo";
import { setGatewaySession } from "./lib/api";
import { Gate } from "./lib/Gate";
import { useGateway } from "./lib/useGateway";

const LABELS = [
  "PERSON",
  "ORG",
  "JOB",
  "EMAIL_ADDRESS",
  "LOCATION",
  "AMOUNT",
  "DATE_TIME",
  "UNIVERSITY",
  "PHONE_NUMBER",
  "URL",
  "IBAN",
  "SSN",
];

export default function App() {
  const gate = useGateway();

  // Every /api call carries the admission id the gateway handed us.
  useEffect(() => {
    setGatewaySession(gate.sessionId);
  }, [gate.sessionId]);

  return (
    <div className="page">
      <header className="hero">
        <p className="eyebrow">NLP / privacy engineering</p>
        <h1>Anonymizer</h1>
        <p className="lede">
          Finds sensitive information in free text and replaces it with labelled
          placeholders, by combining pre-trained language models with rule-based
          matching.
        </p>
        <div className="labels">
          {LABELS.map((label) => (
            <span key={label} className="chip chip--quiet">
              {label}
            </span>
          ))}
        </div>
      </header>

      <Gate gate={gate} />

      <Demo admitted={gate.state === "admitted"} />

      <section className="card">
        <header className="card__head">
          <h2>How it works</h2>
          <p className="muted">
            Rules for things with a format, models for things with meaning.
          </p>
        </header>
        <div className="flow">
          <div className="flow__step">
            <h3>1. Detect</h3>
            <p>
              Several detectors read the same text. Regular expressions match
              fixed shapes such as an email address, phone number or IBAN. Language
              models find open-class entities like people, organisations and places,
              where identity depends on context rather than form.
            </p>
          </div>
          <div className="flow__step">
            <h3>2. Resolve</h3>
            <p>
              Detectors can claim overlapping text, so their results are ranked and
              merged: rules win over model guesses, then the longer match wins. What
              comes out is a set of non-overlapping spans.
            </p>
          </div>
          <div className="flow__step">
            <h3>3. Replace</h3>
            <p>
              Each span becomes its <code>&lt;LABEL&gt;</code> placeholder. Spans are
              replaced from right to left so that earlier edits never shift the
              positions of the ones still to come.
            </p>
          </div>
        </div>
      </section>

      <footer className="foot">
        <p className="muted">
          Text is processed in memory and never stored. Model inference runs on a
          single machine, so visitors are admitted a few at a time.
        </p>
      </footer>
    </div>
  );
}
