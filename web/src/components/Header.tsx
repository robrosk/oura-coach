import { useState, useRef, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { disconnectOura } from '../lib/api';

export function Header() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);
  const location = useLocation();
  const desktopSettingsRef = useRef<HTMLDivElement>(null);
  const mobileSettingsRef = useRef<HTMLDivElement>(null);

  const { user, isAuthenticated, logout } = useAuth();

  const isActive = (path: string) => location.pathname === path;

  const navLinks = [
    { path: '/', label: 'Home' },
    { path: '/privacy', label: 'Privacy' },
    { path: '/terms', label: 'Terms' },
  ];

  // Close settings dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      const target = event.target as Node;
      const clickedOutsideDesktop = desktopSettingsRef.current && !desktopSettingsRef.current.contains(target);
      const clickedOutsideMobile = mobileSettingsRef.current && !mobileSettingsRef.current.contains(target);

      if (clickedOutsideDesktop && clickedOutsideMobile) {
        setSettingsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleDisconnect = async () => {
    if (disconnecting) return;

    setDisconnecting(true);
    try {
      await disconnectOura();
      setSettingsOpen(false);
      window.location.href = '/app';
    } catch (err) {
      console.error('Failed to disconnect:', err);
      alert('Failed to disconnect. Please try again.');
      setDisconnecting(false);
    }
  };

  const handleSignOut = () => {
    setSettingsOpen(false);
    logout();
  };

  const SettingsIcon = ({ className }: { className?: string }) => (
    <svg
      className={className}
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
      />
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
      />
    </svg>
  );

  return (
    <header className="bg-surface border-b border-border">
      <nav className="max-w-4xl mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          {/* Logo */}
          <Link
            to="/"
            className="text-xl font-bold text-text-primary hover:text-accent transition-colors"
          >
            <span className="text-accent">O</span>ura Coach
          </Link>

          {/* Desktop nav + settings */}
          <div className="hidden md:flex items-center gap-6">
            {navLinks.map((link) => (
              <Link
                key={link.path}
                to={link.path}
                className={`text-sm font-medium transition-colors ${
                  isActive(link.path)
                    ? 'text-accent'
                    : 'text-text-secondary hover:text-text-primary'
                }`}
              >
                {link.label}
              </Link>
            ))}

            {/* Auth section */}
            {isAuthenticated ? (
              <div className="relative" ref={desktopSettingsRef}>
                <button
                  onClick={() => setSettingsOpen(!settingsOpen)}
                  className="flex items-center gap-2 text-text-secondary hover:text-text-primary transition-colors"
                  aria-label="Settings"
                >
                  {user?.picture ? (
                    <img
                      src={user.picture}
                      alt={user.name || 'Profile'}
                      className="w-6 h-6 rounded-full"
                    />
                  ) : (
                    <div className="w-6 h-6 rounded-full bg-accent/20 flex items-center justify-center">
                      <span className="text-xs text-accent font-medium">
                        {user?.email?.[0]?.toUpperCase() || '?'}
                      </span>
                    </div>
                  )}
                  <SettingsIcon className="w-[18px] h-[18px]" />
                </button>

                {/* Dropdown menu */}
                {settingsOpen && (
                  <div className="absolute right-0 top-full mt-2 w-56 bg-surface border border-border rounded-lg shadow-lg py-1 z-50">
                    {/* User info */}
                    <div className="px-4 py-2 border-b border-border">
                      <p className="text-sm font-medium text-text-primary truncate">
                        {user?.name || 'User'}
                      </p>
                      <p className="text-xs text-text-muted truncate">
                        {user?.email}
                      </p>
                    </div>

                    {/* Actions */}
                    <button
                      onClick={handleDisconnect}
                      disabled={disconnecting}
                      className="w-full px-4 py-2 text-left text-sm text-text-secondary hover:text-text-primary hover:bg-surface-elevated transition-colors disabled:opacity-50"
                    >
                      {disconnecting ? 'Disconnecting...' : 'Disconnect Oura'}
                    </button>
                    <button
                      onClick={handleSignOut}
                      className="w-full px-4 py-2 text-left text-sm text-error hover:bg-surface-elevated transition-colors"
                    >
                      Sign Out
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <Link
                to="/login"
                className="text-sm font-medium text-accent hover:text-accent-hover transition-colors"
              >
                Sign In
              </Link>
            )}
          </div>

          {/* Mobile: Settings + Menu buttons */}
          <div className="flex md:hidden items-center gap-2">
            {/* Settings button (only show if authenticated) */}
            {isAuthenticated && (
              <div className="relative" ref={mobileSettingsRef}>
                <button
                  onClick={() => setSettingsOpen(!settingsOpen)}
                  className="p-2 text-text-secondary hover:text-text-primary"
                  aria-label="Settings"
                >
                  {user?.picture ? (
                    <img
                      src={user.picture}
                      alt={user.name || 'Profile'}
                      className="w-6 h-6 rounded-full"
                    />
                  ) : (
                    <SettingsIcon className="w-6 h-6" />
                  )}
                </button>

                {/* Mobile dropdown */}
                {settingsOpen && (
                  <div className="absolute right-0 top-full mt-2 w-56 bg-surface border border-border rounded-lg shadow-lg py-1 z-50">
                    {/* User info */}
                    <div className="px-4 py-3 border-b border-border">
                      <p className="text-base font-medium text-text-primary truncate">
                        {user?.name || 'User'}
                      </p>
                      <p className="text-sm text-text-muted truncate">
                        {user?.email}
                      </p>
                    </div>

                    <button
                      onClick={handleDisconnect}
                      disabled={disconnecting}
                      className="w-full px-4 py-3 text-left text-base text-text-secondary hover:text-text-primary hover:bg-surface-elevated transition-colors disabled:opacity-50"
                    >
                      {disconnecting ? 'Disconnecting...' : 'Disconnect Oura'}
                    </button>
                    <button
                      onClick={handleSignOut}
                      className="w-full px-4 py-3 text-left text-base text-error hover:bg-surface-elevated transition-colors"
                    >
                      Sign Out
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* Hamburger menu button */}
            <button
              onClick={() => setMenuOpen(!menuOpen)}
              className="p-2 text-text-secondary hover:text-text-primary"
              aria-label="Toggle menu"
            >
              <svg
                className="w-6 h-6"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                {menuOpen ? (
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                ) : (
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 6h16M4 12h16M4 18h16"
                  />
                )}
              </svg>
            </button>
          </div>
        </div>

        {/* Mobile nav */}
        {menuOpen && (
          <div className="md:hidden mt-4 pt-4 border-t border-border">
            {navLinks.map((link) => (
              <Link
                key={link.path}
                to={link.path}
                onClick={() => setMenuOpen(false)}
                className={`block py-3 text-base font-medium transition-colors ${
                  isActive(link.path)
                    ? 'text-accent'
                    : 'text-text-secondary hover:text-text-primary'
                }`}
              >
                {link.label}
              </Link>
            ))}
            {!isAuthenticated && (
              <Link
                to="/login"
                onClick={() => setMenuOpen(false)}
                className="block py-3 text-base font-medium text-accent hover:text-accent-hover transition-colors"
              >
                Sign In
              </Link>
            )}
          </div>
        )}
      </nav>
    </header>
  );
}
