import React from 'react';
import { useAuth } from '../../context/AuthContext';
import { LogOut, User } from 'lucide-react';

const Header = () => {
  const { user, logout } = useAuth();

  const handleLogout = () => {
    logout();
  };

  // Function to get display name in priority order
  const getDisplayName = () => {
    // 1. Try username first (preferred)
    if (user?.username && user.username.trim()) {
      return user.username;
    }
    // 2. If no username, extract name from email before @
    if (user?.email) {
      return user.email.split('@')[0];
    }
    // 3. Fallback to "User"
    return 'User';
  };

  return (
    <header className="bg-background-card border-b border-background-dark/80">
      <div className="px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 flex items-center justify-center">
              <img
                src="/logo.png"
                alt="Smart Campus Connect"
                className="w-8 h-8 object-contain"
                onError={e => {
                  e.target.style.display = 'none';
                  e.target.nextSibling.style.display = 'flex';
                }}
              />
              <div
                className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center"
                style={{ display: 'none' }}
              >
                <span className="text-white font-semibold text-sm">SC</span>
              </div>
            </div>
            <h1 className="text-xl font-semibold text-accent">
              Smart Campus Connect
            </h1>
          </div>

          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2 text-gray-300">
              <User className="h-4 w-4" />
              <span className="text-sm font-medium">
                Welcome, {getDisplayName()}
              </span>
            </div>
            <button
              onClick={handleLogout}
              className="flex items-center space-x-2 px-3 py-1 text-accent hover:text-white rounded-md hover:bg-primary-600 transition-colors"
              title="Logout"
            >
              <LogOut className="h-4 w-4" />
              <span className="text-sm">Logout</span>
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
