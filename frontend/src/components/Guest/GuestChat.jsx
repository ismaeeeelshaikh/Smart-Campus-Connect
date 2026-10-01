import React from 'react';
import { Link } from 'react-router-dom';
import { Info } from 'lucide-react';
import Header from '../Layout/Header';
import ChatInterface from '../Chat/ChatInterface';
import { useGuestChat } from '../../hooks/useGuestChat';

const GuestChat = () => {
  const { messages, loading, error, sendMessage } = useGuestChat();

  return (
    <div className="h-screen flex flex-col">
      <Header guest />
      <div className="bg-background-card border-b border-background-dark/80 px-6 py-2 flex items-center gap-2 text-sm text-gray-400">
        <Info className="h-4 w-4 flex-shrink-0 text-primary-500" />
        <span>
          You're chatting as a guest, so this chat isn't saved. APSIT students can{' '}
          <Link to="/login" className="text-primary-500 hover:underline">sign in</Link>{' '}
          with their college email to keep their chats.
        </span>
      </div>
      <div className="flex-1 flex overflow-hidden">
        <ChatInterface
          messages={messages}
          onSendMessage={sendMessage}
          loading={loading}
          error={error}
          currentSession={null}
          isNewChat
        />
      </div>
    </div>
  );
};

export default GuestChat;
