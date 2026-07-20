import {
  EXTENDED_COMPARISON,
  GENERALISATION,
  REQUIRED_COMPARISON,
  type Row,
} from "../lib/results";

function ScoreTable({ rows }: { rows: Row[] }) {
  return (
    <div className="table__scroll">
      <table className="table">
        <thead>
          <tr>
            <th>Configuration</th>
            <th className="table__num">Precision</th>
            <th className="table__num">Recall</th>
            <th className="table__num">F1</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={row.name}
              className={row.highlight ? "table__row--lead" : undefined}
            >
              <td>
                <span className="table__name">{row.name}</span>
                {row.note && <span className="table__note">{row.note}</span>}
              </td>
              <td className="table__num">{row.precision}</td>
              <td className="table__num">{row.recall}</td>
              <td className="table__num table__num--strong">{row.f1}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Benchmark() {
  return (
    <section className="card">
      <header className="card__head">
        <h2>What the benchmark found</h2>
        <p className="muted">
          Scored against labelled data: precision, recall and F1 per entity label.
          Recall is the number that matters, because a miss is a leak while a false
          positive only over-redacts.
        </p>
      </header>

      <h3 className="section__title">Two models, measured alone</h3>
      <p className="section__lede">
        Both models get the same input and nothing is added, so the difference
        between them is the models and only the models.
      </p>
      <ScoreTable rows={REQUIRED_COMPARISON} />
      <p className="callout">
        <b>The smaller model wins, but not because it is the better model.</b> The
        transformer is stronger on the entity types both cover. It scores zero on
        dates and money because it is fine-tuned on CoNLL-2003, whose scheme has only
        four entity types. It lost on label coverage, not on quality.
      </p>

      <h3 className="section__title">Testing that conclusion</h3>
      <p className="section__lede">
        Two objections to the result above can be measured rather than argued. These
        are reported separately and never folded into the comparison.
      </p>
      <ScoreTable rows={EXTENDED_COMPARISON} />
      <p className="section__lede">
        Running a transformer trained on OntoNotes, the same scheme spaCy uses,
        settles the first objection: on equal footing the transformer is the stronger
        model. The architecture was never the problem. A zero-shot model, which takes
        its label names at inference time, settles the second: JOB and UNIVERSITY go
        from unreachable to 0.91 and 0.86.
      </p>

      <h3 className="section__title">The finding worth leading with</h3>
      <p className="section__lede">
        The provided texts are built around well-known entities, which are almost
        certainly inside every model's training data. So a second set of 22 texts was
        written with every entity invented, covering all twelve labels across several
        European countries.
      </p>
      <div className="table__scroll">
        <table className="table">
          <thead>
            <tr>
              <th>Configuration</th>
              <th className="table__num">Provided set</th>
              <th className="table__num">Invented entities</th>
            </tr>
          </thead>
          <tbody>
            {GENERALISATION.map((row) => (
              <tr
                key={row.name}
                className={row.highlight ? "table__row--lead" : undefined}
              >
                <td>
                  <span className="table__name">{row.name}</span>
                </td>
                <td className="table__num">{row.provided}</td>
                <td className="table__num table__num--strong">{row.own}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="callout">
        <b>Scores fall by about a third once the entities are invented.</b> That is a
        statement about how NER benchmarks flatter models that have memorised their
        training data, not about these two models in particular. The zero-shot
        configuration scores the same on both sets, which is exactly what
        generalisation looks like.
      </p>
    </section>
  );
}
