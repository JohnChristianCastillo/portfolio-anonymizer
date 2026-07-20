import { ENTITY_METHODS, METHOD_LABELS } from "../lib/results";

export function Methods() {
  return (
    <section className="card">
      <header className="card__head">
        <h2>Why each entity is detected the way it is</h2>
        <p className="muted">
          The split is not arbitrary. It follows from whether a label is identifiable
          by its form or by its meaning.
        </p>
      </header>

      <p className="section__lede">
        An IBAN is an IBAN whatever sentence surrounds it, so a rule reads it
        perfectly and a model reads it not at all. A person's name is only a name
        because of the words around it, so the reverse holds. Two labels belong to
        neither group: JOB and UNIVERSITY are meaning-based but missing from every
        standard NER scheme, which is what a zero-shot model exists to solve.
      </p>

      <div className="table__scroll">
        <table className="table">
          <thead>
            <tr>
              <th>Entity</th>
              <th>Detected by</th>
              <th>Why</th>
            </tr>
          </thead>
          <tbody>
            {ENTITY_METHODS.map((row) => (
              <tr key={row.entity}>
                <td>
                  <code>{row.entity}</code>
                </td>
                <td>
                  <span className={`badge badge--${row.method}`}>
                    {METHOD_LABELS[row.method]}
                  </span>
                </td>
                <td className="table__why">{row.why}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="callout">
        <b>Where a standard exists, the standard's library does the work.</b>{" "}
        Telephone numbers are parsed and validated per country rather than
        pattern-matched, which is what fixed a bug where a timestamp was read as a
        phone number and cut in half. Check digits are reported but never used to
        reject a detection: a mistyped account number is still an account number, and
        a miss is a leak while an unnecessary redaction costs little.
      </p>
    </section>
  );
}
