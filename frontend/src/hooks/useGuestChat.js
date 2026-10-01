import { useEffect, useRef, useState } from 'react';
import { streamChat } from '../services/stream';

let nextId = 0;
const uid = () => `g${Date.now()}-${nextId++}`;

// Last 4 (question, answer) pairs, so follow-up questions like "what about her qualification?" work
const toHistory = (messages) => {
  const history = [];
  for (let i = 0; i < messages.length - 1; i++) {
    if (messages[i].type === 'user' && messages[i + 1].type === 'ai' && !messages[i + 1].streaming) {
      history.push({ question: messages[i].content, answer: messages[i + 1].content });
      i++;
    }
  }
  return history.slice(-4);
};

// Guest chat lives only in this page's memory: it's gone when the tab is closed or reloaded
export const useGuestChat = () => {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [failedQuestion, setFailedQuestion] = useState(null);
  const abortRef = useRef(null);

  useEffect(() => () => abortRef.current?.abort(), []);

  const sendMessage = async (question) => {
    if (loading || !question.trim()) return;
    setError(null);
    setFailedQuestion(null);
    const history = toHistory(messages);
    const now = new Date().toISOString();
    const userMsg = { id: uid(), type: 'user', content: question, timestamp: now };
    const aiId = uid();
    setMessages((prev) => [...prev, userMsg, { id: aiId, type: 'ai', content: '', sources: [], streaming: true, timestamp: now }]);
    const updateAi = (fn) => setMessages((prev) => prev.map((m) => (m.id === aiId ? fn(m) : m)));
    setLoading(true);
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      const done = await streamChat('/guest/chat/stream', { question, history }, {
        signal: controller.signal,
        onToken: (piece) => updateAi((m) => ({ ...m, content: m.content + piece })),
      });
      updateAi((m) => ({ ...m, content: done.answer, sources: done.sources || [], streaming: false }));
    } catch (err) {
      if (err.name === 'AbortError') return;
      setError(err.message || 'Could not get an answer. Please try again.');
      setFailedQuestion(question);
      setMessages((prev) => prev.filter((m) => m.id !== aiId && m.id !== userMsg.id));
    } finally {
      setLoading(false);
    }
  };

  return {
    messages,
    loading,
    error,
    failedQuestion,
    sendMessage,
    dismissError: () => {
      setError(null);
      setFailedQuestion(null);
    },
  };
};
