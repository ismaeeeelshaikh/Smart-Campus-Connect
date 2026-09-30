import { useState, useEffect } from 'react';
import { chatAPI } from '../services/api';

export const useChat = () => {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const loadHistory = async () => {
    try {
      const response = await chatAPI.getHistory();
      const history = response.data.chats.map(chat => ([
        { type: 'user', content: chat.question, timestamp: chat.timestamp },
        { type: 'ai', content: chat.answer, timestamp: chat.timestamp }
      ])).flat();
      setMessages(history);
    } catch (err) {
      console.error('Failed to load chat history:', err);
    }
  };

  const sendMessage = async (message) => {
    setLoading(true);
    setError(null);

    // Add user message immediately
    const userMessage = { type: 'user', content: message, timestamp: new Date().toISOString() };
    setMessages(prev => [...prev, userMessage]);

    try {
      const response = await chatAPI.sendMessage(message);
      const aiMessage = { 
        type: 'ai', 
        content: response.data.answer, 
        timestamp: response.data.timestamp 
      };
      setMessages(prev => [...prev, aiMessage]);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to send message');
      // Remove the user message if sending failed
      setMessages(prev => prev.filter(msg => msg !== userMessage));
    } finally {
      setLoading(false);
    }
  };

  const clearChat = () => {
    setMessages([]);
  };

  useEffect(() => {
    loadHistory();
  }, []);

  return { messages, loading, error, sendMessage, clearChat, loadHistory };
};
