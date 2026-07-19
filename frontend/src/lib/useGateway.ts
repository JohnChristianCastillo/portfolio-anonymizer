import { useEffect, useRef, useState } from "react";

// Admission is only meaningful behind the gateway (production). In local dev there
// is no gateway, so this stays off and the app runs open. Turned on by
// VITE_GATEWAY_ADMISSION=1 in the production build.
const ENABLED = import.meta.env.VITE_GATEWAY_ADMISSION === "1";
// Which app policy the gateway applies (and counts us against).
const APP_SLUG = "anonymizer";

export type GateState =
  | "connecting"
  | "queued"
  | "admitted"
  | "full"
  | "maintenance"
  | "offline"
  | "expired";

export type Gate = {
  state: GateState;
  position: number | null;
  sessionId: string | null;
};

type ServerMsg =
  | { type: "queued"; position: number; eta_seconds: number }
  | { type: "admitted"; session_id: string; tier: string; heartbeat_interval_seconds: number }
  | { type: "full" }
  | { type: "maintenance" }
  | { type: "expired"; reason?: string }
  | { type: "error"; reason?: string };

function wsUrl(): string {
  // Same origin as the page: the gateway serves the app and owns /ws. We tell it
  // which app we want so it applies that app's policy.
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${window.location.host}/ws?app=${APP_SLUG}`;
}

const RECONNECT_MS = 4000;

/**
 * Gateway admission for the anonymizer. Mirrors the other portfolio apps: queue
 * position while waiting, the session id once admitted, heartbeats to hold the
 * slot, and reconnection on drops. A no-op (instantly "admitted") in dev.
 *
 * The queue matters here because every request runs model inference on the host
 * machine, so the gateway's concurrency limit is what keeps that load bounded.
 */
export function useGateway(): Gate {
  const [state, setState] = useState<GateState>(ENABLED ? "connecting" : "admitted");
  const [position, setPosition] = useState<number | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);

  const stateRef = useRef<GateState>(state);
  const wsRef = useRef<WebSocket | null>(null);
  const heartbeatRef = useRef<number | null>(null);
  const reconnectRef = useRef<number | null>(null);
  const disposed = useRef(false);

  function setGate(s: GateState) {
    stateRef.current = s;
    setState(s);
  }

  useEffect(() => {
    if (!ENABLED) return;
    disposed.current = false;

    function stopHeartbeat() {
      if (heartbeatRef.current !== null) {
        clearInterval(heartbeatRef.current);
        heartbeatRef.current = null;
      }
    }

    function connect() {
      if (disposed.current) return;
      if (stateRef.current !== "admitted") setGate("connecting");
      const ws = new WebSocket(wsUrl());
      wsRef.current = ws;

      ws.onmessage = (ev) => {
        let msg: ServerMsg;
        try {
          msg = JSON.parse(ev.data) as ServerMsg;
        } catch {
          return;
        }
        if (msg.type === "queued") {
          setGate("queued");
          setPosition(msg.position);
        } else if (msg.type === "admitted") {
          setGate("admitted");
          setSessionId(msg.session_id);
          setPosition(null);
          stopHeartbeat();
          const interval = (msg.heartbeat_interval_seconds || 15) * 1000;
          heartbeatRef.current = window.setInterval(() => {
            if (ws.readyState === WebSocket.OPEN) {
              ws.send(JSON.stringify({ type: "heartbeat" }));
            }
          }, interval);
        } else if (msg.type === "full") {
          setGate("full");
        } else if (msg.type === "maintenance") {
          setGate("maintenance");
        } else if (msg.type === "expired") {
          setGate("expired");
          setSessionId(null);
          stopHeartbeat();
        }
      };

      ws.onclose = () => {
        stopHeartbeat();
        if (disposed.current) return;
        // The server closes the socket after full/maintenance/expired: keep that
        // terminal state and do not reconnect. Any other drop = offline, retry.
        if (["full", "maintenance", "expired"].includes(stateRef.current)) return;
        setGate("offline");
        setSessionId(null);
        reconnectRef.current = window.setTimeout(connect, RECONNECT_MS);
      };

      ws.onerror = () => {
        try {
          ws.close();
        } catch {
          // onclose handles state
        }
      };
    }

    connect();
    return () => {
      disposed.current = true;
      stopHeartbeat();
      if (reconnectRef.current !== null) clearTimeout(reconnectRef.current);
      wsRef.current?.close();
    };
  }, []);

  return { state, position, sessionId };
}
