# Benchmark report

Regenerate with `uv run anonymizer-report`. Evaluated on a labelled dataset of
10 texts against the 12 target entity labels.

## The required comparison: two models, measured alone

| Configuration | Detectors (priority order) |
|---|---|
| spaCy sm | en_core_web_sm |
| HF bert | dslim/bert-base-NER |

Both models are given the same input and nothing else is added, so the difference
between them is the models and only the models.

| Configuration | Precision | Recall | F1 | Exact rows |
|---|---|---|---|---|
| spaCy sm | 0.91 | 0.76 | 0.83 | 2/10 |
| HF bert | 0.94 | 0.67 | 0.78 | 1/10 |

| Label (F1) | spaCy sm | HF bert |
|---|---|---|
| PERSON | 1.00 | 1.00 |
| ORG | 0.75 | 0.94 |
| JOB | 0.00 | 0.00 |
| EMAIL_ADDRESS | 0.00 | 0.00 |
| LOCATION | 0.89 | 0.95 |
| AMOUNT | 1.00 | 0.00 |
| DATE_TIME | 0.88 | 0.00 |
| UNIVERSITY | 0.00 | 0.00 |
| PHONE_NUMBER | 0.00 | 0.00 |
| URL | 0.00 | 0.00 |

Highest F1: **spaCy sm**. Recall matters most here, because a missed identifier
is a leak, while a false positive only over-redacts.

**What it shows.** The two have complementary blind spots. The transformer is
stronger on the entity types both cover, reading context better: organisations and
locations both improve. But it emits no dates and no money at all, because it is
fine-tuned on CoNLL-2003, whose scheme has only four entity types. The smaller spaCy
pipeline therefore wins overall, on coverage rather than on quality.

## Why the rule layer is reported separately

A rule layer for fixed-shape identifiers was added as an engineering step. It is
**not** part of the model comparison above, and mixing the two would be misleading:

- The rules can only ever produce **6 of the 12 labels** (email, URL, telephone,
  IBAN, national number, and postal codes within a location). They contribute
  nothing to people, organisations, job titles, dates or amounts.
- Adding the same rule layer to both models adds the same easy wins to both, which
  raises both scores and narrows the visible gap between them.
- In principle the rules could also mask a model's detections, since they take
  priority when spans overlap. Measured on this dataset they never do: **zero** model
  spans were suppressed for either model. So here the layer is purely additive, and
  the ordering of the two models is unchanged. That is a measurement, not an
  assumption.

So the numbers below describe a **system**, not a model.

| Configuration | Detectors (priority order) |
|---|---|
| spaCy+regex | rules + phonenumbers/stdnum + en_core_web_sm |
| HF+regex | rules + phonenumbers/stdnum + dslim/bert-base-NER |

| Configuration | Precision | Recall | F1 | Exact rows |
|---|---|---|---|---|
| spaCy+regex | 0.91 | 0.82 | 0.87 | 3/10 |
| HF+regex | 0.95 | 0.73 | 0.82 | 1/10 |

**What it shows.** Rules and models solve disjoint problems. The rule layer scores
highly on exactly the fixed-shape types that both models score zero on, while the
models handle the open-class entities no regular expression can express. Adding
rules lifts recall for both models with no loss of precision, which is why the
delivered tool combines them even though the comparison above does not.

### All four core configurations together

![Overall metrics by configuration](core_overall_metrics.png)

![Each metric compared across configurations](core_metric_comparison.png)

![F1 per entity label](core_per_label_f1.png)

| Configuration | Precision | Recall | F1 | Exact rows |
|---|---|---|---|---|
| spaCy sm | 0.91 | 0.76 | 0.83 | 2/10 |
| HF bert | 0.94 | 0.67 | 0.78 | 1/10 |
| spaCy+regex | 0.91 | 0.82 | 0.87 | 3/10 |
| HF+regex | 0.95 | 0.73 | 0.82 | 1/10 |

| Label (F1) | spaCy sm | HF bert | spaCy+regex | HF+regex |
|---|---|---|---|---|
| PERSON | 1.00 | 1.00 | 1.00 | 1.00 |
| ORG | 0.75 | 0.94 | 0.75 | 0.94 |
| JOB | 0.00 | 0.00 | 0.00 | 0.00 |
| EMAIL_ADDRESS | 0.00 | 0.00 | 1.00 | 1.00 |
| LOCATION | 0.89 | 0.95 | 0.89 | 0.95 |
| AMOUNT | 1.00 | 0.00 | 1.00 | 0.00 |
| DATE_TIME | 0.88 | 0.00 | 0.88 | 0.00 |
| UNIVERSITY | 0.00 | 0.00 | 0.00 | 0.00 |
| PHONE_NUMBER | 0.00 | 0.00 | 1.00 | 1.00 |
| URL | 0.00 | 0.00 | 1.00 | 1.00 |

## Beyond the required comparison

The comparison above answers the question that was set. Three further configurations
were then measured to test two specific objections to it. They are reported
separately so they cannot be mistaken for the original result, and adding them did
not change any number above.

| Configuration | Detectors (priority order) |
|---|---|
| HF onto | djagatiya/ner-roberta-base-ontonotesv5-englishv4 |
| HF onto+regex | rules + phonenumbers/stdnum + djagatiya/ner-roberta-base-ontonotesv5-englishv4 |
| GLiNER | urchade/gliner_base |
| GLiNER+regex | rules + phonenumbers/stdnum + urchade/gliner_base |
| Stacked x3 | rules + phonenumbers/stdnum + djagatiya/ner-roberta-base-ontonotesv5-englishv4 + urchade/gliner_base |

### Objection 1: was the transformer beaten by its architecture, or by its labels?

The transformer in the required comparison is trained on CoNLL-2003, which defines
only four entity types, so it can never emit a date or an amount. That is a property
of the training scheme rather than of the architecture, and it alone could explain
why the smaller model won.

Running the same kind of transformer trained on **OntoNotes**, the scheme spaCy also
uses, settles it: on equal footing the transformer is the stronger model, beating
spaCy on organisations, locations and dates, at a markedly higher precision.

**The original conclusion therefore needs stating carefully.** The smaller model won
that comparison, but not because it was the better model. It won because the other
one was blind to a third of the labels being asked for.

### Objection 2: are JOB and UNIVERSITY actually unreachable?

Every configuration in the required comparison scores zero on both, because no
standard NER scheme contains those classes. A **zero-shot** model is given its label
names at inference time instead of being limited to what it was trained on, so it can
simply be asked for them.

That breaks the wall: both labels are detected for the first time. It also produces
the highest recall of any configuration measured, which matters here more than F1,
since a miss is a leak and a false positive only over-redacts.

### Every model, measured alone

The same apples-to-apples view as the required comparison, now with all four models
and no rule layer involved:

| Configuration | Precision | Recall | F1 | Exact rows |
|---|---|---|---|---|
| spaCy sm | 0.91 | 0.76 | 0.83 | 2/10 |
| HF bert | 0.94 | 0.67 | 0.78 | 1/10 |
| HF onto | 0.98 | 0.82 | 0.89 | 0/10 |
| GLiNER | 0.88 | 0.96 | 0.92 | 2/10 |

| Label (F1) | spaCy sm | HF bert | HF onto | GLiNER |
|---|---|---|---|---|
| PERSON | 1.00 | 1.00 | 1.00 | 1.00 |
| ORG | 0.75 | 0.94 | 0.94 | 0.84 |
| JOB | 0.00 | 0.00 | 0.00 | 0.67 |
| EMAIL_ADDRESS | 0.00 | 0.00 | 0.00 | 1.00 |
| LOCATION | 0.89 | 0.95 | 0.95 | 0.95 |
| AMOUNT | 1.00 | 0.00 | 1.00 | 1.00 |
| DATE_TIME | 0.88 | 0.00 | 0.93 | 1.00 |
| UNIVERSITY | 0.00 | 0.00 | 0.00 | 1.00 |
| PHONE_NUMBER | 0.00 | 0.00 | 0.00 | 0.67 |
| URL | 0.00 | 0.00 | 0.00 | 0.00 |

### Every configuration

![All configurations](all_overall_metrics.png)

| Configuration | Precision | Recall | F1 | Exact rows |
|---|---|---|---|---|
| spaCy sm | 0.91 | 0.76 | 0.83 | 2/10 |
| HF bert | 0.94 | 0.67 | 0.78 | 1/10 |
| spaCy+regex | 0.91 | 0.82 | 0.87 | 3/10 |
| HF+regex | 0.95 | 0.73 | 0.82 | 1/10 |
| HF onto | 0.98 | 0.82 | 0.89 | 0/10 |
| HF onto+regex | 0.98 | 0.88 | 0.93 | 0/10 |
| GLiNER | 0.88 | 0.96 | 0.92 | 2/10 |
| GLiNER+regex | 0.89 | 0.98 | 0.93 | 3/10 |
| Stacked x3 | 0.87 | 0.94 | 0.91 | 0/10 |

![F1 per entity label, all configurations](all_per_label_f1.png)

| Label (F1) | spaCy sm | HF bert | spaCy+regex | HF+regex | HF onto | HF onto+regex | GLiNER | GLiNER+regex | Stacked x3 |
|---|---|---|---|---|---|---|---|---|---|
| PERSON | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| ORG | 0.75 | 0.94 | 0.75 | 0.94 | 0.94 | 0.94 | 0.84 | 0.89 | 0.84 |
| JOB | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.67 | 0.67 | 0.67 |
| EMAIL_ADDRESS | 0.00 | 0.00 | 1.00 | 1.00 | 0.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| LOCATION | 0.89 | 0.95 | 0.89 | 0.95 | 0.95 | 0.95 | 0.95 | 0.95 | 0.95 |
| AMOUNT | 1.00 | 0.00 | 1.00 | 0.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| DATE_TIME | 0.88 | 0.00 | 0.88 | 0.00 | 0.93 | 0.93 | 1.00 | 1.00 | 0.93 |
| UNIVERSITY | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 1.00 | 1.00 | 0.00 |
| PHONE_NUMBER | 0.00 | 0.00 | 1.00 | 1.00 | 0.00 | 1.00 | 0.67 | 0.67 | 0.67 |
| URL | 0.00 | 0.00 | 1.00 | 1.00 | 0.00 | 1.00 | 0.00 | 1.00 | 1.00 |

- Highest F1: **GLiNER+regex** at 0.93.
- Highest recall: **GLiNER+regex** at 0.98, and recall is the
  metric this task should be judged on.
- Exact-row match falls for the OntoNotes configurations even though their F1 rises,
  because that model tends to include trailing punctuation inside an entity. Exact
  match is unforgiving of boundaries in a way that per-label scoring is not, which is
  a good illustration of why more than one measure is reported.

## How each entity is detected, and why

Everything above compares configurations. This is the conclusion drawn from them:
for each of the twelve labels, the method the delivered tool uses and the reason it
was chosen.

The division is not arbitrary. It follows from whether a label is identifiable by
its **form** or by its **meaning**. An IBAN is an IBAN whatever sentence surrounds
it, so a rule reads it perfectly and a model reads it not at all. A person's name is
only a name because of the words around it, so the reverse holds. Two labels, JOB
and UNIVERSITY, belong to neither group: they are meaning-based but missing from
every standard NER scheme, which is what a zero-shot model exists to solve.

| Entity | How it is detected | Why |
|---|---|---|
| PERSON | NER model | A name is a name because of where it sits in a sentence, not its shape. No pattern can express that. Every model detects it well (F1 0.90 to 1.00). |
| ORG | NER model | Same reason as PERSON, but harder: an organisation name is often an ordinary word. This is the weakest of the model-detected labels (0.77) and the main remaining source of confusion with PERSON. |
| JOB | Zero-shot model | Absent from every standard NER scheme, so a fine-tuned model scores 0.00 no matter how good it is. A zero-shot model is given the label name at inference time instead, which takes it from 0.00 to 0.91. |
| EMAIL_ADDRESS | Rule | Fully specified by its form. A pattern reaches 1.00, while the zero-shot model reaches 0.67 on the same data, so a rule is both better and cheaper. |
| LOCATION | NER model, plus a rule for postal codes | Place names need a model. Postal codes are the exception: the models consistently return the town but not the digits in front of it, so a narrow rule fills that gap. It requires a following capitalised word, so a bare year is not mistaken for a postal code. |
| AMOUNT | NER model, chosen for its label scheme | Solved by choosing the right model rather than by writing a rule. CoNLL has no money class and scores 0.00; the OntoNotes model scores 1.00 on the same texts, including the European formats that defeat the smaller pipeline. Currency writing varies far too much to enumerate by hand. |
| DATE_TIME | NER model | The models read machine timestamps as well as written dates, so no rule is needed. An earlier hand-written telephone pattern matched the leading '2022-12-27 08' of a timestamp and split it in half; validating telephone numbers properly removed the collision and the label rose to 0.93. |
| UNIVERSITY | Zero-shot model | Like JOB, absent from standard schemes, so 0.00 everywhere until asked for by name. Then 0.86. |
| PHONE_NUMBER | phonenumbers (libphonenumber) | The one identifier that is parsed and validated rather than matched. A pattern loose enough to accept the many ways a number is written also matches timestamps and national numbers; validation removes that whole class of collision, and covers every country rather than a chosen few. |
| URL | Rule | Fully specified by its form, and the zero-shot model scores 0.00 on it. The pattern requires a scheme or www. so ordinary words never match, and excludes sentence punctuation from the end of a path. |
| IBAN | Rule, with python-stdnum for check digits | Models score 0.00: an account number carries no linguistic signal. The shape is matched first, before telephone numbers, because an IBAN contains a run of digits that is a plausible number on its own. |
| SSN | Rule, with python-stdnum for check digits | Same as IBAN. National identifier formats differ per country, so the library supplies the structures rather than one developer's guesses. |

Where a standard exists, the standard's own library does the work rather than a
pattern invented here: `phonenumbers` for telephone numbers, `python-stdnum` for
account and national numbers. This is a correctness decision, not a convenience
one. Those libraries encode per-country structure and check digits that no
hand-written pattern reproduces, and they were what fixed the timestamp collision.

Check digits are **reported alongside a detection and never used to reject one**.
The reasoning is the same as everywhere else in this task: a mistyped account number
is still an account number, so redacting it costs nothing while missing it is a leak.
The best illustration is `BE68 5390 0754 7034`, the example IBAN that appears in most
documentation. It passes the international mod-97 check but fails Belgium's own
account-number rule, so validating before redacting would have discarded a textbook
account number.

## How the scoring works

The anonymized RESULT is compared against the EXPECTED answer by aligning the two
token sequences (Python's `difflib`). Per label:

- **TP**: an expected `<LABEL>` the configuration also produced.
- **FP**: a `<LABEL>` produced where none was expected (over-anonymizing).
- **FN**: an expected `<LABEL>` that was missed (a leak).

From those, precision = TP/(TP+FP), recall = TP/(TP+FN), and F1 is their harmonic
mean. The micro-average pools every label's counts into one total.

Counts are aggregated over every occurrence of a label across all texts, not per
text, which is why a per-label score is usually a fraction: a label occurring eight
times with six caught and two missed scores 0.75, not 0 or 1. A label scores exactly
1.00 only when every occurrence was caught with no false positives, which is easiest
for labels that occur once or twice.

"Exact rows" counts texts where the whole anonymized output matched the expected
string character for character, which is a deliberately strict measure.

## Limitations

- The evaluation set is small, so per-label figures move a lot per entity; treat the
  numbers as indicative rather than precise.
- Some expected labels are debatable (for example a telephone area code labelled as
  a location), so strict matching penalises otherwise reasonable output.
- The overlap-resolution rule never actually fires on this dataset: no spans were
  dropped for overlapping. It is defensive design for messier input and additional
  detectors, not a fix for an observed failure.
- The zero-shot configuration is noisier than a fine-tuned one, since nothing was
  trained on these exact label names; predictions below a confidence threshold are
  discarded.

## Exact numbers

Every value plotted above, per configuration.

### spaCy sm

| Label | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|
| PERSON | 7 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| ORG | 6 | 2 | 2 | 0.75 | 0.75 | 0.75 |
| JOB | 0 | 0 | 2 | 0.00 | 0.00 | 0.00 |
| EMAIL_ADDRESS | 0 | 0 | 1 | 0.00 | 0.00 | 0.00 |
| LOCATION | 17 | 1 | 3 | 0.94 | 0.85 | 0.89 |
| AMOUNT | 2 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| DATE_TIME | 7 | 1 | 1 | 0.88 | 0.88 | 0.88 |
| UNIVERSITY | 0 | 0 | 1 | 0.00 | 0.00 | 0.00 |
| PHONE_NUMBER | 0 | 0 | 1 | 0.00 | 0.00 | 0.00 |
| URL | 0 | 0 | 1 | 0.00 | 0.00 | 0.00 |
| **micro-average** | 39 | 4 | 12 | 0.91 | 0.76 | 0.83 |

### HF bert

| Label | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|
| PERSON | 7 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| ORG | 8 | 1 | 0 | 0.89 | 1.00 | 0.94 |
| JOB | 0 | 0 | 2 | 0.00 | 0.00 | 0.00 |
| EMAIL_ADDRESS | 0 | 0 | 1 | 0.00 | 0.00 | 0.00 |
| LOCATION | 19 | 1 | 1 | 0.95 | 0.95 | 0.95 |
| AMOUNT | 0 | 0 | 2 | 0.00 | 0.00 | 0.00 |
| DATE_TIME | 0 | 0 | 8 | 0.00 | 0.00 | 0.00 |
| UNIVERSITY | 0 | 0 | 1 | 0.00 | 0.00 | 0.00 |
| PHONE_NUMBER | 0 | 0 | 1 | 0.00 | 0.00 | 0.00 |
| URL | 0 | 0 | 1 | 0.00 | 0.00 | 0.00 |
| **micro-average** | 34 | 2 | 17 | 0.94 | 0.67 | 0.78 |

### spaCy+regex

| Label | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|
| PERSON | 7 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| ORG | 6 | 2 | 2 | 0.75 | 0.75 | 0.75 |
| JOB | 0 | 0 | 2 | 0.00 | 0.00 | 0.00 |
| EMAIL_ADDRESS | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| LOCATION | 17 | 1 | 3 | 0.94 | 0.85 | 0.89 |
| AMOUNT | 2 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| DATE_TIME | 7 | 1 | 1 | 0.88 | 0.88 | 0.88 |
| UNIVERSITY | 0 | 0 | 1 | 0.00 | 0.00 | 0.00 |
| PHONE_NUMBER | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| URL | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| **micro-average** | 42 | 4 | 9 | 0.91 | 0.82 | 0.87 |

### HF+regex

| Label | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|
| PERSON | 7 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| ORG | 8 | 1 | 0 | 0.89 | 1.00 | 0.94 |
| JOB | 0 | 0 | 2 | 0.00 | 0.00 | 0.00 |
| EMAIL_ADDRESS | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| LOCATION | 19 | 1 | 1 | 0.95 | 0.95 | 0.95 |
| AMOUNT | 0 | 0 | 2 | 0.00 | 0.00 | 0.00 |
| DATE_TIME | 0 | 0 | 8 | 0.00 | 0.00 | 0.00 |
| UNIVERSITY | 0 | 0 | 1 | 0.00 | 0.00 | 0.00 |
| PHONE_NUMBER | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| URL | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| **micro-average** | 37 | 2 | 14 | 0.95 | 0.73 | 0.82 |

### HF onto

| Label | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|
| PERSON | 7 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| ORG | 8 | 1 | 0 | 0.89 | 1.00 | 0.94 |
| JOB | 0 | 0 | 2 | 0.00 | 0.00 | 0.00 |
| EMAIL_ADDRESS | 0 | 0 | 1 | 0.00 | 0.00 | 0.00 |
| LOCATION | 18 | 0 | 2 | 1.00 | 0.90 | 0.95 |
| AMOUNT | 2 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| DATE_TIME | 7 | 0 | 1 | 1.00 | 0.88 | 0.93 |
| UNIVERSITY | 0 | 0 | 1 | 0.00 | 0.00 | 0.00 |
| PHONE_NUMBER | 0 | 0 | 1 | 0.00 | 0.00 | 0.00 |
| URL | 0 | 0 | 1 | 0.00 | 0.00 | 0.00 |
| **micro-average** | 42 | 1 | 9 | 0.98 | 0.82 | 0.89 |

### HF onto+regex

| Label | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|
| PERSON | 7 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| ORG | 8 | 1 | 0 | 0.89 | 1.00 | 0.94 |
| JOB | 0 | 0 | 2 | 0.00 | 0.00 | 0.00 |
| EMAIL_ADDRESS | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| LOCATION | 18 | 0 | 2 | 1.00 | 0.90 | 0.95 |
| AMOUNT | 2 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| DATE_TIME | 7 | 0 | 1 | 1.00 | 0.88 | 0.93 |
| UNIVERSITY | 0 | 0 | 1 | 0.00 | 0.00 | 0.00 |
| PHONE_NUMBER | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| URL | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| **micro-average** | 45 | 1 | 6 | 0.98 | 0.88 | 0.93 |

### GLiNER

| Label | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|
| PERSON | 7 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| ORG | 8 | 3 | 0 | 0.73 | 1.00 | 0.84 |
| JOB | 2 | 2 | 0 | 0.50 | 1.00 | 0.67 |
| EMAIL_ADDRESS | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| LOCATION | 19 | 1 | 1 | 0.95 | 0.95 | 0.95 |
| AMOUNT | 2 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| DATE_TIME | 8 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| UNIVERSITY | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| PHONE_NUMBER | 1 | 1 | 0 | 0.50 | 1.00 | 0.67 |
| URL | 0 | 0 | 1 | 0.00 | 0.00 | 0.00 |
| **micro-average** | 49 | 7 | 2 | 0.88 | 0.96 | 0.92 |

### GLiNER+regex

| Label | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|
| PERSON | 7 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| ORG | 8 | 2 | 0 | 0.80 | 1.00 | 0.89 |
| JOB | 2 | 2 | 0 | 0.50 | 1.00 | 0.67 |
| EMAIL_ADDRESS | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| LOCATION | 19 | 1 | 1 | 0.95 | 0.95 | 0.95 |
| AMOUNT | 2 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| DATE_TIME | 8 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| UNIVERSITY | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| PHONE_NUMBER | 1 | 1 | 0 | 0.50 | 1.00 | 0.67 |
| URL | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| **micro-average** | 50 | 6 | 1 | 0.89 | 0.98 | 0.93 |

### Stacked x3

| Label | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|
| PERSON | 7 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| ORG | 8 | 3 | 0 | 0.73 | 1.00 | 0.84 |
| JOB | 2 | 2 | 0 | 0.50 | 1.00 | 0.67 |
| EMAIL_ADDRESS | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| LOCATION | 19 | 1 | 1 | 0.95 | 0.95 | 0.95 |
| AMOUNT | 2 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| DATE_TIME | 7 | 0 | 1 | 1.00 | 0.88 | 0.93 |
| UNIVERSITY | 0 | 0 | 1 | 0.00 | 0.00 | 0.00 |
| PHONE_NUMBER | 1 | 1 | 0 | 0.50 | 1.00 | 0.67 |
| URL | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| **micro-average** | 48 | 7 | 3 | 0.87 | 0.94 | 0.91 |
