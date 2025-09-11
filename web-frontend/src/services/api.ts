import { fetchEventSource } from '@microsoft/fetch-event-source';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://web-server-304334704110.us-central1.run.app';

export const streamChat = (message: string, sessionId: string, onMessage: (event: any) => void, onStop: () => void, onError: (err: any) => void) => {
  const eventSource = new EventSource(
    `${BASE_URL}/chat?message=${encodeURIComponent(
      message,
    )}&sessionId=${sessionId}`,
  );

  eventSource.addEventListener('content', (event) => onMessage({ event: 'content', data: event.data }));
  eventSource.addEventListener('thought', (event) => onMessage({ event: 'thought', data: event.data }));
  eventSource.addEventListener('tool_code', (event) => onMessage({ event: 'tool_code', data: event.data }));
  eventSource.addEventListener('tool_result', (event) => onMessage({ event: 'tool_result', data: event.data }));
  eventSource.addEventListener('end', () => {
    eventSource.close();
    onStop();
  });
  eventSource.addEventListener('error', (err) => {
    eventSource.close();
    onError(err);
  });

  return eventSource;
}

export const streamMultiCityChat = (body: any, sessionId: string, onMessage: (event: any) => void, onStop: () => void, onError: (err: any) => void) => {
  fetchEventSource(`${BASE_URL}/multi-city?sessionId=${sessionId}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
    onmessage: onMessage,
    onclose: onStop,
    onerror: onError,
    openWhenHidden: true,
  });
}
