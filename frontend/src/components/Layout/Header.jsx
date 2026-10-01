import React from 'react';
import { Link } from 'react-router-dom';
import { LogIn, Menu } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import WebsiteSyncPanel from '../Admin/WebsiteSyncPanel';
import { Wordmark } from '../Brand/Brand';

/**
 * Top bar of the chat area.
 * - student chat: current chat title, admin "Website sync" button, menu button (mobile)
 * - guest chat (`guest`): brand + "Sign in"
 */
const Header = ({ guest = false, title, onMenu, hasPdf = false }) => {
  const { user } = useAuth();

  if (guest) {
    return (
      <header className="flex items-center justify-between gap-3 border-b border-line bg-white/90 px-4 py-3 backdrop-blur sm:px-6">
        <Wordmark size={36} subtitle="APSIT Thane" />
        <div className="flex shrink-0 items-center gap-3">
          <span className="hidden rounded-full bg-gold-100 px-2.5 py-1 text-xs font-semibold text-gold-800 sm:inline">Guest</span>
          <Link to="/login" className="btn-outline whitespace-nowrap px-3 py-2">
            <LogIn className="h-4 w-4" /> Sign in
          </Link>
        </div>
      </header>
    );
  }

  return (
    <header className="flex min-h-[60px] items-center justify-between gap-3 border-b border-line bg-white/90 px-4 py-2.5 backdrop-blur sm:px-6">
      <div className="flex min-w-0 items-center gap-2">
        <button type="button" onClick={onMenu} className="-ml-1 rounded-lg p-2 text-ink-500 hover:bg-paper-100 lg:hidden" aria-label="Open chats">
          <Menu className="h-5 w-5" />
        </button>
        <div className="min-w-0">
          <h1 className="truncate font-serif text-base font-semibold text-teal-900 sm:text-lg">{title || 'New chat'}</h1>
          <p className="hidden text-xs text-ink-400 sm:block">
            {hasPdf ? 'Answers from your PDF and apsit.edu.in' : 'Answers from apsit.edu.in · sources linked'}
          </p>
        </div>
      </div>
      {user?.is_admin && <WebsiteSyncPanel />}
    </header>
  );
};

export default Header;
