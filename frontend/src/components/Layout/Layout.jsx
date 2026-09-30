import React from 'react';
import Header from './Header';
import Sidebar from '../Sidebar/Sidebar';
import ChatInterface from '../Chat/ChatInterface';
import { useChat } from '../../hooks/useChat';

const Layout = () => {
  const { clearChat } = useChat();

  const handleNewChat = () => {
    clearChat();
  };

  return (
    <div className="h-screen flex flex-col bg-background-dark text-gray-100 transition-colors duration-300">
      <Header />
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar inherits dark/card color from index.css */}
        <Sidebar onNewChat={handleNewChat} />
        {/* Main chat area - ensures pure dark bg */}
        <div className="flex-1 bg-background-dark min-h-0">
          <ChatInterface onNewChat={handleNewChat} />
        </div>
      </div>
    </div>
  );
};

export default Layout;
