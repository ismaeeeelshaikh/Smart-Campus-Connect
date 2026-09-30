import React from 'react';
import ReactMarkdown from 'react-markdown';
import Linkify from 'react-linkify';
import { User, Bot } from 'lucide-react';

const ChatMessage = ({ message }) => {
  const isUser = message.type === 'user';

  // Custom link style consistent with theme
  const componentDecorator = (decoratedHref, decoratedText, key) => (
    <a
      key={key}
      href={decoratedHref}
      target="_blank"
      rel="noopener noreferrer"
      className="text-primary-500 hover:text-primary-600 underline break-words"
      style={{ textDecoration: 'underline' }}
    >
      {decoratedText}
    </a>
  );

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div className={`flex max-w-3xl ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
        <div className={`flex-shrink-0 ${isUser ? 'ml-3' : 'mr-3'}`}>
          <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
            isUser ? 'bg-primary-600 text-white' : 'bg-background-card border border-background-dark text-gray-300'
          }`}>
            {isUser ? (
              <User className="h-4 w-4" />
            ) : (
              <>
                <img
                  src="/logo.png"
                  alt="Smart Campus Connect"
                  className="w-6 h-6 object-contain"
                  onError={(e) => {
                    e.target.style.display = 'none';
                    e.target.nextSibling.style.display = 'block';
                  }}
                />
                <Bot className="h-4 w-4 text-gray-500" style={{ display: 'none' }} />
              </>
            )}
          </div>
        </div>

        <div className={`rounded-lg px-4 py-2 max-w-full ${
          isUser
            ? 'bg-primary-600 text-white'
            : 'bg-background-card border border-background-dark text-gray-100'
        }`}>
          {isUser ? (
            <div className="text-sm whitespace-pre-wrap break-words">
              <Linkify componentDecorator={componentDecorator}>
                {message.content}
              </Linkify>
            </div>
          ) : (
            <div className="text-sm prose prose-sm max-w-none break-words">
              <ReactMarkdown
                components={{
                  a: ({ href, children }) => (
                    <a
                      href={href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary-500 hover:text-primary-600 underline"
                      style={{ textDecoration: 'underline' }}
                    >
                      {children}
                    </a>
                  ),
                  p: ({ children }) => (
                    <p className="mb-2">
                      <Linkify componentDecorator={componentDecorator}>
                        {children}
                      </Linkify>
                    </p>
                  ),
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          )}
          <div className={`text-xs mt-1 ${
            isUser ? 'text-primary-300' : 'text-gray-400'
          }`}>
            {new Date(message.timestamp).toLocaleTimeString()}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatMessage;
