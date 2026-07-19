import type { Gate as GateInfo } from "./useGateway";

const MESSAGES: Record<string, string> = {
  connecting: "Connecting...",
  queued: "You are in the queue.",
  full: "This app is at capacity right now. Please try again shortly.",
  maintenance: "The app is temporarily unavailable for maintenance.",
  offline: "Connection lost. Reconnecting...",
  expired: "Your session expired. Reload the page to rejoin.",
};

/**
 * Banner shown whenever the visitor is not admitted. Every request runs model
 * inference on one machine, so the gateway admits a limited number of people at a
 * time; this explains the wait rather than leaving the page looking broken.
 */
export function Gate({ gate }: { gate: GateInfo }) {
  if (gate.state === "admitted") return null;

  const detail =
    gate.state === "queued" && gate.position !== null
      ? `Position ${gate.position}.`
      : null;

  return (
    <div className={`gate gate--${gate.state}`} role="status">
      <span className="gate__dot" aria-hidden="true" />
      <span>
        {MESSAGES[gate.state] ?? "Waiting..."} {detail}
      </span>
    </div>
  );
}
