'use client';

import { useEffect, useRef, useCallback, useState } from 'react';

export interface VoiceServerMessage {
  success?: boolean;
  response?: string;
  message?: string;
  action?: string;
  tasks?: Array<Record<string, unknown>>;
  requiresConfirmation?: boolean;
  error?: string;
}

const RECONNECT_MS = 2500;

export const useWebSocket = (url: string) => {
  const wsRef = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<VoiceServerMessage | null>(null);
  const messageCallbackRef = useRef<((message: VoiceServerMessage) => void) | null>(null);
  const stoppedRef = useRef(false);

  useEffect(() => {
    stoppedRef.current = false;
    let reconnectTimer: ReturnType<typeof setTimeout> | undefined;

    const connect = () => {
      if (stoppedRef.current) return;

      const ws = new WebSocket(url);

      ws.onopen = () => {
        setIsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as VoiceServerMessage;
          setLastMessage(message);
          messageCallbackRef.current?.(message);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      ws.onerror = () => {
        setIsConnected(false);
      };

      ws.onclose = () => {
        setIsConnected(false);
        wsRef.current = null;
        if (!stoppedRef.current) {
          reconnectTimer = setTimeout(connect, RECONNECT_MS);
        }
      };

      wsRef.current = ws;
    };

    connect();

    return () => {
      stoppedRef.current = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      const w = wsRef.current;
      if (w && w.readyState === WebSocket.OPEN) {
        w.close();
      }
      wsRef.current = null;
    };
  }, [url]);

  const send = useCallback((message: Record<string, unknown>) => {
    const w = wsRef.current;
    if (w && w.readyState === WebSocket.OPEN) {
      w.send(JSON.stringify(message));
    } else {
      console.error('WebSocket is not connected');
    }
  }, []);

  const onMessage = useCallback((callback: (message: VoiceServerMessage) => void) => {
    messageCallbackRef.current = callback;
  }, []);

  return {
    isConnected,
    send,
    lastMessage,
    onMessage,
  };
};
