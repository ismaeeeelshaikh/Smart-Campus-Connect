import { useState } from 'react';
import { guestAPI } from '../services/api';

// Last 4 (question, answer) pairs, so follow-up questions like "what about her qualification?" work
const toHistory = (messages) => {
  const history = [];
  for (let i = 0; i < messages.length - 1; i++) {
    if (messages[i].type === 'user' && messages[i + 1].type === 'ai') {
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

  const sendMessage = async (question) => {
    if (loading) return;
    setError(null);
    const history = toHistory(messages);
    setMessages((prev) => [...prev, { type: 'user', content: question, timestamp: new Date().toISOString() }]);
    setLoading(true);
    try {
      const response = await guestAPI.chat(question, history);
      setMessages((prev) => [...prev, { type: 'ai', content: response.data.answer, timestamp: new Date().toISOString() }]);
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Could not get an answer. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return { messages, loading, error, sendMessage };
};
