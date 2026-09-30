import { useState, useEffect } from 'react';
import { chatSessionAPI } from '../services/api';

export const useChatSessions = () => {
  const [sessions, setSessions] = useState([]);
  const [currentSession, setCurrentSession] = useState(null);
  const [currentMessages, setCurrentMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isNewChat, setIsNewChat] = useState(true); // NEW: Track if this is a fresh chat

  const loadSessions = async () => {
    try {
      const response = await chatSessionAPI.getSessions();
      setSessions(response.data.sessions);
      
      // If no sessions, start with empty new chat
      if (response.data.sessions.length === 0) {
        setIsNewChat(true);
        setCurrentSession(null);
        setCurrentMessages([]);
      }
    } catch (err) {
      console.error('Failed to load sessions:', err);
      setError('Failed to load chat sessions');
    }
  };

  const createNewSession = async (title = 'New Chat') => {
    try {
      // For manual "New Chat" button - create empty session
      const response = await chatSessionAPI.createSession(title);
      const newSession = response.data;
      setSessions(prev => [newSession, ...prev]);
      setCurrentSession(newSession);
      setCurrentMessages([]);
      setIsNewChat(false);
      return newSession;
    } catch (err) {
      console.error('Failed to create session:', err);
      setError('Failed to create new chat');
      throw err;
    }
  };

  const startNewChat = () => {
    // NEW: ChatGPT-like new chat - just clear interface, don't create session yet
    setCurrentSession(null);
    setCurrentMessages([]);
    setIsNewChat(true);
    setError(null);
  };

  const loadSession = async (sessionId) => {
    try {
      setLoading(true);
      const response = await chatSessionAPI.getSession(sessionId);
      const sessionDetail = response.data;
      
      setCurrentSession(sessionDetail);
      setIsNewChat(false);
      
      // Convert messages to frontend format
      const messages = sessionDetail.messages.flatMap(msg => [
        { type: 'user', content: msg.question, timestamp: msg.timestamp },
        { type: 'ai', content: msg.answer, timestamp: msg.timestamp }
      ]);
      
      setCurrentMessages(messages);
    } catch (err) {
      console.error('Failed to load session:', err);
      setError('Failed to load chat session');
    } finally {
      setLoading(false);
    }
  };

  const sendMessage = async (message) => {
    setLoading(true);
    setError(null);
    // Add user message immediately
    const userMessage = { type: 'user', content: message, timestamp: new Date().toISOString() };
    setCurrentMessages(prev => [...prev, userMessage]);

    try {
      if (isNewChat) {
        // NEW: ChatGPT-like experience - create session with first message
        console.log('Starting new chat session with first message:', message);
        const response = await chatSessionAPI.startChatSession(message);
        
        const newSession = response.data.session;
        const aiMessageResponse = response.data.message;
        
        // Update state
        setCurrentSession(newSession);
        setSessions(prev => [newSession, ...prev]);
        setIsNewChat(false);
        
        const aiMessage = { 
          type: 'ai', 
          content: aiMessageResponse.answer, 
          timestamp: aiMessageResponse.timestamp 
        };
        setCurrentMessages(prev => [...prev, aiMessage]);
        
      } else {
        // Existing session - send message normally
        if (!currentSession) {
          throw new Error('No active chat session');
        }
        
        const response = await chatSessionAPI.sendMessage(currentSession.id, message);
        const aiMessage = { 
          type: 'ai', 
          content: response.data.answer, 
          timestamp: response.data.timestamp 
        };
        setCurrentMessages(prev => [...prev, aiMessage]);
        
        // Update session in list (move to top)
        setSessions(prev => {
          const updated = prev.map(s => 
            s.id === currentSession.id 
              ? { ...s, updated_at: new Date().toISOString(), message_count: (s.message_count || 0) + 1 } 
              : s
          );
          return updated.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));
        });
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to send message');
      // Remove the user message if sending failed
      setCurrentMessages(prev => prev.filter(msg => msg !== userMessage));
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const updateSessionTitle = async (sessionId, title) => {
    try {
      await chatSessionAPI.updateSessionTitle(sessionId, title);
      setSessions(prev => prev.map(s => s.id === sessionId ? { ...s, title } : s));
      if (currentSession && currentSession.id === sessionId) {
        setCurrentSession(prev => ({ ...prev, title }));
      }
    } catch (err) {
      console.error('Failed to update session title:', err);
      setError('Failed to update chat title');
    }
  };

  const deleteSession = async (sessionId) => {
    try {
      await chatSessionAPI.deleteSession(sessionId);
      setSessions(prev => prev.filter(s => s.id !== sessionId));
      
      if (currentSession && currentSession.id === sessionId) {
        // After deleting current session, start fresh new chat
        startNewChat();
      }
    } catch (err)
 {
      console.error('Failed to delete session:', err);
      setError('Failed to delete chat session');
    }
  };

  useEffect(() => {
    loadSessions();
  }, []);

  return {
    sessions,
    currentSession,
    currentMessages,
    loading,
    error,
    isNewChat, // NEW: Expose whether this is a new unsaved chat
    createNewSession, // OLD: Manual session creation
    startNewChat, // NEW: ChatGPT-like new chat
    loadSession,
    sendMessage, // UPDATED: Handles both new and existing sessions
    updateSessionTitle,
    deleteSession,
    loadSessions
  };
};