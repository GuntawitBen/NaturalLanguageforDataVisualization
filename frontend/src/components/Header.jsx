import { useState, useEffect, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Home, Database, Clock, LogOut, ChevronDown, Zap } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigationGuard } from '../contexts/NavigationGuardContext';
import './Header.css';

export default function Header() {
  const location = useLocation();
  const navigate = useNavigate();
  const { logout, user } = useAuth();
  const { confirmNavigation } = useNavigationGuard();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);

  const getInitials = () => {
    if (!user?.name) return 'U';
    const nameParts = user.name.trim().split(' ');
    if (nameParts.length === 1) {
      return nameParts[0].charAt(0).toUpperCase();
    }
    const firstInitial = nameParts[0].charAt(0).toUpperCase();
    const lastInitial = nameParts[nameParts.length - 1].charAt(0).toUpperCase();
    return firstInitial + lastInitial;
  };

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setDropdownOpen(false);
      }
    };

    if (dropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [dropdownOpen]);

  const navItems = [
    { path: '/', icon: Home, label: 'Home' },
    { path: '/datasets', icon: Database, label: 'Datasets' },
    { path: '/history', icon: Clock, label: 'Recents' },
  ];

  const handleLogout = () => {
    logout();
    navigate('/signin');
  };

  return (
    <div className="header-wrapper">
    <header className="header">
      {/* Left: Logo */}
      <button
        onClick={(e) => {
          e.preventDefault();
          if (location.pathname !== '/') {
            confirmNavigation(() => navigate('/'));
          }
        }}
        className="header-logo"
      >
        <div className="logo-mark">
          <Zap size={14} />
        </div>
        <span className="logo-text">phebe</span>
        <span className="logo-version">v1.0</span>
      </button>

      {/* Center: Navigation */}
      <nav className="header-nav">
        <div className="nav-track">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            return (
              <button
                key={item.path}
                onClick={(e) => {
                  e.preventDefault();
                  if (location.pathname !== item.path) {
                    confirmNavigation(() => navigate(item.path));
                  }
                }}
                className={`nav-item ${isActive ? 'active' : ''}`}
              >
                <Icon size={14} strokeWidth={2} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </div>
      </nav>

      {/* Right: User Menu */}
      <div className="header-actions" ref={dropdownRef}>
        <button
          className={`user-trigger ${dropdownOpen ? 'open' : ''}`}
          onClick={() => setDropdownOpen(!dropdownOpen)}
        >
          <div className="user-avatar">
            <span>{getInitials()}</span>
          </div>
          <span className="user-name">{user?.name?.split(' ')[0] || 'User'}</span>
          <ChevronDown size={14} className="user-chevron" />
        </button>

        {dropdownOpen && (
          <div className="dropdown">
            <div className="dropdown-header">
              <span className="dropdown-label">Signed in as</span>
              <span className="dropdown-email">{user?.email || 'user@email.com'}</span>
            </div>
            <div className="dropdown-divider" />
            <button onClick={handleLogout} className="dropdown-action logout">
              <LogOut size={14} />
              <span>Log out</span>
            </button>
          </div>
        )}
      </div>
    </header>
    </div>
  );
}
