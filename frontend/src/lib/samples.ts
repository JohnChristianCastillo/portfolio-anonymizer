/**
 * Ready-made inputs, so a visitor can see varied output without having to invent
 * text. Each one is chosen to show something different: the rule-based detectors,
 * the model-based ones, a case the tool handles badly, and a control with nothing
 * to find.
 *
 * Everything here is fictional: invented people, `.example` domains (a reserved
 * documentation TLD), and made-up account and phone numbers.
 */
export type Sample = {
  name: string;
  /** What this example is meant to reveal, shown as a tooltip. */
  hint: string;
  text: string;
};

export const samples: Sample[] = [
  {
    name: "Business email",
    hint: "A bit of everything: person, organisation, place, email, phone and URL.",
    text:
      "Hi Sofie, please forward the signed contract to Maarten De Vos at Contoso " +
      "Belgium in Ghent. He can be reached at maarten.devos@contoso.example or on " +
      "+32 471 22 33 44, and the portal is at www.contoso.example/contracts.",
  },
  {
    name: "Bank details",
    hint: "Structured identifiers that rules catch and models miss: IBAN and a national number.",
    text:
      "Payment received from Lena Peeters, national number 85.07.12-034.51, on " +
      "account BE68 5390 0754 7034. Confirmation was sent to l.peeters@example.org " +
      "on 4 March 2026.",
  },
  {
    name: "Acquisition news",
    hint: "Dates and amounts. Switch detectors to HF bert and watch these disappear.",
    text:
      "Northwind Systems was acquired by Acme Robotics for $4.2 billion in March " +
      "2019. The transaction closed on 12 June 2019 after a review by regulators " +
      "in Brussels.",
  },
  {
    name: "Support ticket",
    hint: "Shows the known gap: the job title is missed, and the university is only labelled as an organisation.",
    text:
      "Ticket 4821: Elena Rossi, a senior research engineer at Ghent University, " +
      "reported that her account was locked after travelling to Lisbon. Reach her " +
      "at e.rossi@example.org.",
  },
  {
    name: "Nothing sensitive",
    hint: "A control case: there is nothing to redact, so nothing should be.",
    text:
      "The report has been uploaded to the shared drive. Please review the summary " +
      "and add any comments before the next stand-up.",
  },
];
