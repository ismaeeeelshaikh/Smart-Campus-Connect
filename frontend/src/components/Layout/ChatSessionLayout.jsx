import React, { useState } from 'react';
import Header from './Header';
import ChatSessionsSidebar from '../Sidebar/ChatSessionsSidebar';
import ChatInterface from '../Chat/ChatInterface';
import { useChatSessions } from '../../hooks/useChatSessions';
import { useAuth } from '../../context/AuthContext';
import { displayName } from '../../services/validation';

const ChatSessionLayout = () => {
  const chat = useChatSessions();
  const { user, logout, updateUser } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(false); // mobile drawer

  const closeAfter = (fn) => (...args) => {
    setSidebarOpen(false);
    return fn(...args);
  };

  const sidebar = (
    <ChatSessionsSidebar
      sessions={chat.sessions}
      sessionsLoaded={chat.sessionsLoaded}
      currentSession={chat.currentSession}
      onNewChat={closeAfter(chat.startNewChat)}
      onSelectSession={closeAfter(chat.loadSession)}
      onUpdateTitle={chat.updateSessionTitle}
      onDeleteSession={chat.deleteSession}
      user={user}
      onLogout={logout}
      onUserUpdated={updateUser}
    />
  );

  const firstName = displayName(user).split(/[\s._-]/)[0];

  return (
    <div className="flex h-screen overflow-hidden bg-paper">
      {/* Desktop sidebar */}
      <div className="hidden lg:block">{sidebar}</div>

      {/* Mobile drawer */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-teal-950/40" onClick={() => setSidebarOpen(false)} />
          <div className="absolute inset-y-0 left-0 animate-fade-up shadow-lift">{sidebar}</div>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <Header title={chat.isNewChat ? 'New chat' : chat.currentSession?.title} onMenu={() => setSidebarOpen(true)} />
        <ChatInterface
          messages={chat.currentMessages}
          onSendMessage={chat.sendMessage}
          loading={chat.loading}
          loadingSession={chat.loadingSession}
          error={chat.error}
          failedQuestion={chat.failedQuestion}
          onDismissError={chat.dismissError}
          greeting={firstName ? `Hi ${firstName}, ask anything about APSIT` : 'Ask anything about APSIT'}
        />
      </div>
    </div>
  );
};

export default ChatSessionLayout;
