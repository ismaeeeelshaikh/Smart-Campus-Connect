import React, { useState } from 'react';
import { MessageSquare, Plus, Edit2, Trash2, MoreHorizontal } from 'lucide-react';

const ChatSessionsSidebar = ({ 
  sessions, 
  currentSession, 
  onNewChat, 
  onSelectSession, 
  onUpdateTitle, 
  onDeleteSession 
}) => {
  const [editingId, setEditingId] = useState(null);
  const [editTitle, setEditTitle] = useState('');

  const startEditing = (session) => {
    setEditingId(session.id);
    setEditTitle(session.title);
  };

  const saveTitle = async (sessionId) => {
    if (editTitle.trim()) {
      await onUpdateTitle(sessionId, editTitle.trim());
    }
    setEditingId(null);
  };

  const cancelEditing = () => {
    setEditingId(null);
    setEditTitle('');
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = now - date;
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    return date.toLocaleDateString();
  };

  return (
    <div className="w-80 bg-gray-900 text-white h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-700">
        <button
          onClick={onNewChat}
          className="w-full flex items-center space-x-3 px-4 py-3 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <Plus className="h-5 w-5" />
          <span className="font-medium">New Chat</span>
        </button>
      </div>
      
      {/* Chat Sessions List */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-2">
          {sessions.length === 0 ? (
            <div className="px-4 py-8 text-center text-gray-400">
              <MessageSquare className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">No chats yet</p>
              <p className="text-xs">Start a new conversation</p>
            </div>
          ) : (
            <div className="space-y-1">
              {sessions.map((session) => (
                <div
                  key={session.id}
                  className={`group relative p-3 rounded-lg cursor-pointer transition-colors duration-200 ${
                    currentSession?.id === session.id
                      ? 'bg-gray-700 border-l-4 border-blue-500'
                      : 'hover:bg-gray-800'
                  }`}
                  onClick={() => onSelectSession(session.id)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      {editingId === session.id ? (
                        <div className="flex items-center space-x-2">
                          <input
                            type="text"
                            value={editTitle}
                            onChange={(e) => setEditTitle(e.target.value)}
                            className="flex-1 px-2 py-1 text-sm bg-gray-600 rounded border border-gray-500 focus:outline-none focus:border-blue-500"
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') saveTitle(session.id);
                              if (e.key === 'Escape') cancelEditing();
                            }}
                            onBlur={() => saveTitle(session.id)}
                            autoFocus
                          />
                        </div>
                      ) : (
                        <>
                          <h3 className="font-medium text-sm truncate mb-1">
                            {session.title}
                          </h3>
                          <div className="flex items-center justify-between text-xs text-gray-400">
                            <span>{formatDate(session.updated_at)}</span>
                            {session.message_count > 0 && (
                              <span>{session.message_count} messages</span>
                            )}
                          </div>
                        </>
                      )}
                    </div>
                    
                    {editingId !== session.id && (
                      <div className="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            startEditing(session);
                          }}
                          className="p-1 text-gray-400 hover:text-white rounded"
                          title="Edit title"
                        >
                          <Edit2 className="h-3 w-3" />
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            if (confirm('Are you sure you want to delete this chat?')) {
                              onDeleteSession(session.id);
                            }
                          }}
                          className="p-1 text-gray-400 hover:text-red-400 rounded"
                          title="Delete chat"
                        >
                          <Trash2 className="h-3 w-3" />
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ChatSessionsSidebar;