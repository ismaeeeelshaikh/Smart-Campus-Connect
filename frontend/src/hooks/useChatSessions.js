import { useEffect, useRef, useState } from 'react';
import { chatSessionAPI } from '../services/api';
import { streamChat } from '../services/stream';
import { apiErrorMessage } from '../services/validation';

let nextId = 0;
const uid = () => `m${Date.now()}-${nextId++}`;

export const MAX_PDF_MB = 10; // same limit as the backend (UPLOAD_MAX_MB)

const byNewest = (list) => [...list].sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));

const toMessages = (sessionDetail) =>
  sessionDetail.messages.flatMap((msg) => [
    { id: `q${msg.id}`, type: 'user', content: msg.question, timestamp: msg.timestamp },
    { id: `a${msg.id}`, type: 'ai', content: msg.answer, sources: msg.sources || [], timestamp: msg.timestamp },
  ]);

export const useChatSessions = () => {
  const [sessions, setSessions] = useState([]);
  const [sessionsLoaded, setSessionsLoaded] = useState(false);
  const [currentSession, setCurrentSession] = useState(null);
  const [currentMessages, setCurrentMessages] = useState([]);
  const [loading, setLoading] = useState(false); // waiting for / streaming an answer
  const [loadingSession, setLoadingSession] = useState(false);
  const [error, setError] = useState(null);
  const [failedQuestion, setFailedQuestion] = useState(null); // for "Try again"
  const [isNewChat, setIsNewChat] = useState(true); // a fresh chat isn't saved until the first answer
  const [pdf, setPdf] = useState(null); // the current chat's uploaded PDF: {filename, pages}
  const [uploadingPdf, setUploadingPdf] = useState(null); // file name while a PDF is being read
  const abortRef = useRef(null);
  const viewRef = useRef(0); // changes whenever another chat is opened (to ignore late upload results)

  const stopStreaming = () => {
    abortRef.current?.abort();
    abortRef.current = null;
  };

  const startNewChat = () => {
    stopStreaming();
    viewRef.current += 1;
    setCurrentSession(null);
    setCurrentMessages([]);
    setPdf(null);
    setIsNewChat(true);
    setError(null);
    setFailedQuestion(null);
    setLoading(false);
  };

  const loadSession = async (sessionId) => {
    stopStreaming();
    viewRef.current += 1;
    setLoading(false);
    setLoadingSession(true);
    setError(null);
    setFailedQuestion(null);
    try {
      const response = await chatSessionAPI.getSession(sessionId);
      setCurrentSession(response.data);
      setCurrentMessages(toMessages(response.data));
      setPdf(response.data.document || null);
      setIsNewChat(false);
    } catch (err) {
      setError(apiErrorMessage(err, 'Could not open this chat.'));
    } finally {
      setLoadingSession(false);
    }
  };

  const sendMessage = async (text) => {
    if (loading || !text.trim()) return;
    stopStreaming();
    const controller = new AbortController();
    abortRef.current = controller;

    setLoading(true);
    setError(null);
    setFailedQuestion(null);
    const now = new Date().toISOString();
    const userMsg = { id: uid(), type: 'user', content: text, timestamp: now };
    const aiId = uid();
    setCurrentMessages((prev) => [...prev, userMsg, { id: aiId, type: 'ai', content: '', sources: [], streaming: true, timestamp: now }]);
    const updateAi = (fn) => setCurrentMessages((prev) => prev.map((m) => (m.id === aiId ? fn(m) : m)));
    const onToken = (piece) => updateAi((m) => ({ ...m, content: m.content + piece }));

    try {
      if (isNewChat) {
        const done = await streamChat('/chat-sessions/start/stream', { question: text }, { onToken, signal: controller.signal });
        setCurrentSession(done.session);
        setSessions((prev) => [done.session, ...prev.filter((s) => s.id !== done.session.id)]);
        setIsNewChat(false);
        updateAi((m) => ({ ...m, content: done.message.answer, sources: done.message.sources, streaming: false, timestamp: done.message.timestamp }));
      } else {
        const sessionId = currentSession.id;
        const done = await streamChat(`/chat-sessions/${sessionId}/messages/stream`, { question: text }, { onToken, signal: controller.signal });
        updateAi((m) => ({ ...m, content: done.message.answer, sources: done.message.sources, streaming: false, timestamp: done.message.timestamp }));
        // Move this chat to the top of the list
        setSessions((prev) =>
          byNewest(prev.map((s) =>
            s.id === sessionId ? { ...s, updated_at: new Date().toISOString(), message_count: (s.message_count || 0) + 1 } : s
          ))
        );
      }
    } catch (err) {
      if (err.name === 'AbortError') return; // user switched chats
      setError(err.message || 'Could not get an answer. Please try again.');
      setFailedQuestion(text);
      setCurrentMessages((prev) => prev.filter((m) => m.id !== aiId && m.id !== userMsg.id));
    } finally {
      if (abortRef.current === controller) {
        abortRef.current = null;
        setLoading(false);
      }
    }
  };

  // Attach a PDF: to the open chat, or (on the welcome screen) to a new chat named after the file
  const uploadPdf = async (file) => {
    if (uploadingPdf || loading) return;
    if (!/\.pdf$/i.test(file.name) && file.type !== 'application/pdf') {
      setError('Please choose a PDF file.');
      return;
    }
    if (file.size > MAX_PDF_MB * 1024 * 1024) {
      setError(`The PDF is too large. The limit is ${MAX_PDF_MB} MB.`);
      return;
    }
    const view = viewRef.current;
    setError(null);
    setFailedQuestion(null);
    setUploadingPdf(file.name);
    try {
      if (isNewChat || !currentSession) {
        const { data } = await chatSessionAPI.startWithPdf(file);
        setSessions((prev) => [data.session, ...prev.filter((s) => s.id !== data.session.id)]);
        if (viewRef.current !== view) return; // the user opened another chat meanwhile
        setCurrentSession(data.session);
        setCurrentMessages([]);
        setIsNewChat(false);
        setPdf(data.document);
      } else {
        const sessionId = currentSession.id;
        const { data } = await chatSessionAPI.uploadPdf(sessionId, file);
        setSessions((prev) =>
          byNewest(prev.map((s) => (s.id === sessionId ? { ...s, has_document: true, updated_at: new Date().toISOString() } : s)))
        );
        if (viewRef.current === view) setPdf(data);
      }
    } catch (err) {
      if (viewRef.current === view) setError(apiErrorMessage(err, 'Could not read the PDF. Please try again.'));
    } finally {
      setUploadingPdf(null);
    }
  };

  const removePdf = async () => {
    if (!currentSession || !pdf) return;
    const sessionId = currentSession.id;
    try {
      await chatSessionAPI.removePdf(sessionId);
      setPdf(null);
      if (currentMessages.length === 0) {
        // Nothing else was in this chat: remove it too
        await chatSessionAPI.deleteSession(sessionId).catch(() => {});
        setSessions((prev) => prev.filter((s) => s.id !== sessionId));
        startNewChat();
      } else {
        setSessions((prev) => prev.map((s) => (s.id === sessionId ? { ...s, has_document: false } : s)));
      }
    } catch (err) {
      setError(apiErrorMessage(err, 'Could not remove the PDF.'));
    }
  };

  const updateSessionTitle = async (sessionId, title) => {
    try {
      await chatSessionAPI.updateSessionTitle(sessionId, title);
      setSessions((prev) => prev.map((s) => (s.id === sessionId ? { ...s, title } : s)));
      setCurrentSession((prev) => (prev && prev.id === sessionId ? { ...prev, title } : prev));
    } catch (err) {
      setError(apiErrorMessage(err, 'Could not rename the chat.'));
    }
  };

  const deleteSession = async (sessionId) => {
    try {
      await chatSessionAPI.deleteSession(sessionId);
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      if (currentSession && currentSession.id === sessionId) startNewChat();
    } catch (err) {
      setError(apiErrorMessage(err, 'Could not delete the chat.'));
    }
  };

  // Load the chat list once, when the chat page opens
  useEffect(() => {
    let cancelled = false;
    chatSessionAPI
      .getSessions()
      .then((response) => !cancelled && setSessions(response.data.sessions))
      .catch((err) => !cancelled && setError(apiErrorMessage(err, 'Could not load your chats.')))
      .finally(() => !cancelled && setSessionsLoaded(true));
    return () => {
      cancelled = true;
      abortRef.current?.abort();
    };
  }, []);

  return {
    sessions,
    sessionsLoaded,
    currentSession,
    currentMessages,
    loading,
    loadingSession,
    error,
    failedQuestion,
    isNewChat,
    pdf,
    uploadingPdf,
    startNewChat,
    loadSession,
    sendMessage,
    uploadPdf,
    removePdf,
    updateSessionTitle,
    deleteSession,
    dismissError: () => {
      setError(null);
      setFailedQuestion(null);
    },
  };
};
