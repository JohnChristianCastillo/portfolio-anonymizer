import type { AnonymizeResult, DetectorConfig } from "./types";

// API base. In dev this is "/api" (Vite proxies to the backend). In production the
// app is served under the gateway at /anonymizer, so calls go to "/anonymizer/api".
const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

// The gateway admission session id (from the WebSocket handshake). The gateway
// gates every /api call on it. Null in local dev (no gateway).
let gatewaySessionId: string | null = null;

export function setGatewaySession(id: string | null): void {
  gatewaySessionId = id;
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    ...(init?.headers as Record<string, string>),
  };
  if (init?.body) headers["Content-Type"] = "application/json";
  if (gatewaySessionId) headers["X-Session-Id"] = gatewaySessionId;

  const response = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      if (body?.detail) detail = body.detail;
    } catch {
      // no JSON body
    }
    throw new Error(detail);
  }
  return (await response.json()) as T;
}

export function fetchConfigs(): Promise<DetectorConfig[]> {
  return req<DetectorConfig[]>("/configs");
}

export function anonymize(text: string, config: string): Promise<AnonymizeResult> {
  return req<AnonymizeResult>("/anonymize", {
    method: "POST",
    body: JSON.stringify({ text, config, include_original: true }),
  });
}
