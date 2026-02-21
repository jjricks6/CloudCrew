/**
 * WebSocket hook wrapping react-use-websocket for CloudCrew events.
 *
 * Connects to the API Gateway WebSocket, handles reconnection and heartbeat,
 * and dispatches incoming events to the Zustand agent store.
 */

import { useCallback, useEffect, useMemo, useRef } from "react";
import useWebSocket, { ReadyState } from "react-use-websocket";
import { useAgentStore } from "@/state/stores/agentStore";
import { getIdToken, isAuthEnabled } from "@/lib/auth";
import type { WebSocketEvent, WsStatus } from "@/lib/types";

const WS_URL = import.meta.env.VITE_WS_URL ?? "";
const HEARTBEAT_INTERVAL_MS = 30_000;

const READY_STATE_MAP: Record<ReadyState, WsStatus> = {
  [ReadyState.CONNECTING]: "connecting",
  [ReadyState.OPEN]: "connected",
  [ReadyState.CLOSING]: "disconnected",
  [ReadyState.CLOSED]: "disconnected",
  [ReadyState.UNINSTANTIATED]: "disconnected",
};

/**
 * Build the WebSocket URL, appending auth token when Cognito is enabled.
 * Returns a Promise so react-use-websocket resolves it before connecting.
 */
async function buildSocketUrl(projectId: string): Promise<string> {
  let url = `${WS_URL}?projectId=${projectId}`;
  if (isAuthEnabled()) {
    const token = await getIdToken();
    if (token) {
      url += `&token=${encodeURIComponent(token)}`;
    }
  }
  return url;
}

export function useCloudCrewSocket(projectId: string | undefined) {
  const setWsStatus = useAgentStore((s) => s.setWsStatus);
  const addEvent = useAgentStore((s) => s.addEvent);
  const heartbeatRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // react-use-websocket accepts a callback that returns a Promise<string>
  const getSocketUrl = useMemo(() => {
    if (!projectId || !WS_URL) return null;
    return () => buildSocketUrl(projectId);
  }, [projectId]);

  const { readyState, sendJsonMessage } = useWebSocket(getSocketUrl, {
    shouldReconnect: () => true,
    reconnectAttempts: 20,
    reconnectInterval: (attemptNumber) =>
      Math.min(1000 * 2 ** attemptNumber, 30_000),
    onMessage: (msg) => {
      try {
        const data = JSON.parse(msg.data) as WebSocketEvent;
        addEvent(data);
      } catch {
        // Ignore non-JSON messages (heartbeat ACK, etc.)
      }
    },
  });

  // Map ReadyState to our WsStatus
  useEffect(() => {
    setWsStatus(READY_STATE_MAP[readyState]);
  }, [readyState, setWsStatus]);

  // Heartbeat every 30s when connected
  useEffect(() => {
    if (readyState === ReadyState.OPEN) {
      heartbeatRef.current = setInterval(() => {
        sendJsonMessage({ action: "heartbeat" });
      }, HEARTBEAT_INTERVAL_MS);
    }
    return () => {
      if (heartbeatRef.current) {
        clearInterval(heartbeatRef.current);
        heartbeatRef.current = null;
      }
    };
  }, [readyState, sendJsonMessage]);

  const sendMessage = useCallback(
    (data: Record<string, unknown>) => {
      sendJsonMessage(data);
    },
    [sendJsonMessage],
  );

  return { status: READY_STATE_MAP[readyState], sendMessage };
}
