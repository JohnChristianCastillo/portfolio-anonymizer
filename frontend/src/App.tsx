import { Benchmark } from "./components/Benchmark";
import { Demo } from "./components/Demo";
import { Methods } from "./components/Methods";
import { SiteNav } from "./components/SiteNav";
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

  // Register the session before children effects run so the first API request
  // already carries the gateway admission id.
  setGatewaySession(gate.sessionId);

  return (
    <div className="page">
      <SiteNav tier={gate.tier} />

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
              merged: a validated identifier outranks a model's guess, then the
              longer match wins. What comes out is a set of non-overlapping spans.
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

      <Benchmark />

      <Methods />

      <section className="card">
        <header className="card__head">
          <h2>What this does not do</h2>
          <p className="muted">
            Worth stating plainly rather than leaving to be discovered.
          </p>
        </header>
        <ul className="limits">
          <li>
            <b>Both evaluation sets are small</b>, at 10 texts and 22. A label that
            appears once and scores 1.00 means one correct detection, not a solved
            problem.
          </li>
          <li>
            <b>English only.</b> The models are English-trained, so no other language
            and no non-Latin script has been evaluated.
          </li>
          <li>
            <b>Organisations are the weakest label</b> the models handle, and are
            still sometimes confused with people, since an organisation name is often
            an ordinary word.
          </li>
          <li>
            <b>The best configuration is not the default.</b> The zero-shot model
            pins an older version of a shared dependency, so it is kept out of the
            lock file and enabled explicitly.
          </li>
          <li>
            <b>Detection is not a guarantee.</b> Anything a detector misses stays in
            the output, which is why recall is the metric this is judged on.
          </li>
        </ul>
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
