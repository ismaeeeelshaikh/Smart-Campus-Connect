import React from 'react';
import Header from './Header';
import ChatSessionsSidebar from '../Sidebar/ChatSessionsSidebar';
import ChatInterface from '../Chat/ChatInterface';
import { useChatSessions } from '../../hooks/useChatSessions';

const ChatSessionLayout = () => {
  const {
    sessions,
    currentSession,
    currentMessages,
    loading,
    error,
    isNewChat,
    startNewChat, // Updated to use startNewChat instead of createNewSession
    loadSession,
    sendMessage,
    updateSessionTitle,
    deleteSession
  } = useChatSessions();

  const handleNewChat = () => {
    // NEW: ChatGPT-like - just start fresh interface
    startNewChat();
  };

  const handleSelectSession = async (sessionId) => {
    try {
      await loadSession(sessionId);
    } catch (error) {
      console.error('Failed to load session:', error);
    }
  };

  // REMOVED: Auto-creation useEffect - no longer needed!

  return (
    <div className="h-screen flex flex-col">
      <Header />
      <div className="flex-1 flex overflow-hidden">
        <ChatSessionsSidebar
          sessions={sessions}
          currentSession={currentSession}
          onNewChat={handleNewChat}
          onSelectSession={handleSelectSession}
          onUpdateTitle={updateSessionTitle}
          onDeleteSession={deleteSession}
          isNewChat={isNewChat} // NEW: Pass isNewChat state
        />
        <ChatInterface
          messages={currentMessages}
          onSendMessage={sendMessage}
          loading={loading}
          error={error}
          currentSession={currentSession}
          isNewChat={isNewChat} // NEW: Pass isNewChat state
        />
      </div>
    </div>
  );
};

export default ChatSessionLayout;