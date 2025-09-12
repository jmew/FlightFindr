import { fetchEventSource } from '@microsoft/fetch-event-source';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

const getAuthHeaders = () => {
    const headers: Record<string, string> = {
        'Content-Type': 'application/json',
    };
    const tokenData = localStorage.getItem('google_auth_token');
    if (tokenData) {
        // Base64 encode the token data to ensure safe transmission in the header.
        const encodedToken = btoa(tokenData);
        headers['Authorization'] = `Bearer ${encodedToken}`;
    }
    return headers;
}

export const streamChat = (message: string, sessionId: string, onMessage: (event: any) => void, onStop: () => void, onError: (err: any) => void) => {
  const url = `${API_BASE_URL}/chat?message=${encodeURIComponent(message)}&sessionId=${sessionId}`;
  fetchEventSource(url, {
    headers: getAuthHeaders(),
    onmessage: onMessage,
    onclose: onStop,
    onerror: onError,
    openWhenHidden: true,
  });
};

export const streamMultiCityChat = (body: any, sessionId: string, onMessage: (event: any) => void, onStop: () => void, onError: (err: any) => void) => {
  fetchEventSource(`${API_BASE_URL}/multi-city?sessionId=${sessionId}`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(body),
    onmessage: onMessage,
    onclose: onStop,
    onerror: onError,
    openWhenHidden: true,
  });
}

export const getSuggestions = async (text: string): Promise<string[]> => {
  const response = await fetch(`${API_BASE_URL}/suggestions?text=${encodeURIComponent(text)}`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    throw new Error('Failed to fetch suggestions');
  }
  return response.json();
};