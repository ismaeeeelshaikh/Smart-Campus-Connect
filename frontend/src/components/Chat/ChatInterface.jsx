import React, { useRef, useEffect } from 'react';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import { Loader2 } from 'lucide-react';

const ChatInterface = ({ messages, onSendMessage, loading, error, currentSession, isNewChat }) => {
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // FIXED: Only show loading if we're not in a new chat state
  if (!currentSession && !isNewChat) {
    return (
      <div className="flex-1 flex items-center justify-center bg-background-dark">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <p className="text-gray-400">Loading chat session...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col h-full bg-background-dark">
      {/* Session Header - Only show if we have a session */}
      {currentSession && (
        <div className="bg-background-card border-b border-background-dark/70 px-6 py-3">
          <h2 className="text-lg font-semibold text-accent">{currentSession.title}</h2>
        </div>
      )}
      
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 bg-background-dark">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <h2 className="text-2xl font-semibold text-accent mb-2">
                Welcome to APSIT AI Assistant
              </h2>
              <p className="text-gray-400 mb-6">
                Ask me anything about A.P. Shah Institute of Technology - admissions, courses, facilities, and more!
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl">
                <button
                  onClick={() => onSendMessage('What IT courses does APSIT offer?')}
                  className="p-4 bg-background-card border border-background-dark rounded-lg hover:bg-primary-600 hover:text-white text-left transition-colors"
                >
                  <div className="font-medium text-accent">IT Courses</div>
                  <div className="text-sm text-gray-400">What IT courses does APSIT offer?</div>
                </button>
                <button
                  onClick={() => onSendMessage('How do I apply for admission to APSIT?')}
                  className="p-4 bg-background-card border border-background-dark rounded-lg hover:bg-primary-600 hover:text-white text-left transition-colors"
                >
                  <div className="font-medium text-accent">Admissions</div>
                  <div className="text-sm text-gray-400">How do I apply for admission?</div>
                </button>
                <button
                  onClick={() => onSendMessage('What facilities are available at APSIT?')}
                  className="p-4 bg-background-card border border-background-dark rounded-lg hover:bg-primary-600 hover:text-white text-left transition-colors"
                >
                  <div className="font-medium text-accent">Facilities</div>
                  <div className="text-sm text-gray-400">What facilities are available?</div>
                </button>
                <button
                  onClick={() => onSendMessage('What is the fee structure at APSIT?')}
                  className="p-4 bg-background-card border border-background-dark rounded-lg hover:bg-primary-600 hover:text-white text-left transition-colors"
                >
                  <div className="font-medium text-accent">Fees</div>
                  <div className="text-sm text-gray-400">What is the fee structure?</div>
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div className="max-w-4xl mx-auto">
            {messages.map((message, index) => (
              <ChatMessage key={index} message={message} />
            ))}
            
            {loading && (
              <div className="flex justify-start mb-4">
                <div className="flex max-w-3xl">
                  <div className="flex-shrink-0 mr-3">
                    <div className="w-8 h-8 rounded-full bg-background-card text-primary-600 flex items-center justify-center">
                      <Loader2 className="h-4 w-4 animate-spin" />
                    </div>
                  </div>
                  <div className="bg-background-card border border-primary-600 text-accent rounded-lg px-4 py-2">
                    <p className="text-sm">Thinking...</p>
                  </div>
                </div>
              </div>
            )}
            
            {error && (
              <div className="max-w-3xl mx-auto mb-4">
                <div className="bg-red-900 border border-red-700 text-red-200 rounded-lg px-4 py-2">
                  <p className="text-sm">{error}</p>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>
      
      <ChatInput onSendMessage={onSendMessage} disabled={loading} />
    </div>
  );
};

export default ChatInterface;
