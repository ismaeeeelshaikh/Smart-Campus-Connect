import React from 'react';
import { Link } from 'react-router-dom';
import { Info } from 'lucide-react';
import Header from '../Layout/Header';
import ChatInterface from '../Chat/ChatInterface';
import { useGuestChat } from '../../hooks/useGuestChat';

const GuestChat = () => {
  const chat = useGuestChat();

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-paper">
      <Header guest />
      <div className="flex items-center gap-2 border-b border-gold-200 bg-gold-50 px-4 py-2 text-xs text-gold-800 sm:px-6 sm:text-sm">
        <Info className="h-4 w-4 shrink-0" />
        <span>
          You&apos;re chatting as a guest, so this chat isn&apos;t saved. APSIT students can{' '}
          <Link to="/login" className="font-semibold underline decoration-gold-400 underline-offset-2">sign in</Link>{' '}
          to keep their chats.
        </span>
      </div>
      <ChatInterface
        messages={chat.messages}
        onSendMessage={chat.sendMessage}
        loading={chat.loading}
        error={chat.error}
        failedQuestion={chat.failedQuestion}
        onDismissError={chat.dismissError}
        greeting="Welcome! Ask anything about APSIT"
      />
    </div>
  );
};

export default GuestChat;
