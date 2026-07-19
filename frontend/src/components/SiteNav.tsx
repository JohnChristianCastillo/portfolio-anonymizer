import type { Tier } from "../lib/useGateway";

// Labels mirror the gateway's own tier vocabulary, so what a visitor sees here reads
// the same as the session table in the admin panel.
const LABELS: Record<Tier, string> = {
  admin: "Admin",
  invited: "Invited",
  anonymous: "Anonymous",
};

const HINTS: Record<Tier, string> = {
  admin: "You are signed in as the owner, with full access.",
  invited: "You are here on an invite link.",
  anonymous: "You are browsing as a guest, on the anonymous slot pool.",
};

// Slim bar above the page: a way back to the portfolio, and which access tier the
// gateway admitted this session under. The badge is omitted until admitted, and in
// dev, where there is no gateway and so no tier to report.
export function SiteNav({ tier }: { tier: Tier | null }) {
  return (
    <nav className="sitenav">
      <a className="sitenav__home" href="https://johnchristiancastillo.com">
        &larr; Portfolio
      </a>
      <span className="sitenav__here">Anonymizer</span>
      {tier && (
        <span className={`tierbadge tierbadge--${tier}`} title={HINTS[tier]}>
          {LABELS[tier]}
        </span>
      )}
    </nav>
  );
}
