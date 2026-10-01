import { API_BASE } from './config';
import { forceLogout, getToken } from './api';

/**
 * POST to a streaming endpoint and read its server-sent events.
 * The backend sends "token" events ({text}) while the answer is written, then one "done"
 * event with the final result, or an "error" event ({detail}).
 *
 * Returns the "done" payload; throws an Error with a user-friendly message on failure.
 */
export async function streamChat(path, body, { onToken, signal } = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
        ...(getToken() ? { Authorization: `Bearer ${getToken()}` } : {}),
      },
      body: JSON.stringify(body),
      signal,
    });
  } catch (err) {
    if (err.name === 'AbortError') throw err;
    throw new Error("Can't reach the server. Please check your connection and try again.");
  }

  if (response.status === 401) {
    forceLogout();
    throw new Error('Your session has expired. Please sign in again.');
  }
  if (!response.ok || !response.body) {
    const data = await response.json().catch(() => ({}));
    throw new Error(typeof data.detail === 'string' ? data.detail : 'Could not get an answer. Please try again.');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let result = null;

  const handleEvent = (raw) => {
    let event = 'message';
    const dataLines = [];
    for (const line of raw.split('\n')) {
      if (line.startsWith('event:')) event = line.slice(6).trim();
      else if (line.startsWith('data:')) dataLines.push(line.slice(5).trimStart());
    }
    if (!dataLines.length) return;
    const data = JSON.parse(dataLines.join('\n'));
    if (event === 'token') onToken?.(data.text);
    else if (event === 'done') result = data;
    else if (event === 'error') throw new Error(data.detail || 'Could not get an answer. Please try again.');
  };

  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, '\n');
    let boundary;
    while ((boundary = buffer.indexOf('\n\n')) !== -1) {
      const raw = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      handleEvent(raw);
    }
  }
  if (buffer.trim()) handleEvent(buffer);
  if (!result) throw new Error('The answer was cut off. Please try again.');
  return result;
}
