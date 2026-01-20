import { useState, useEffect, useRef } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Home, Database, Clock, LogOut, Sparkles } from 'lucide-react';
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

  // Get user initials (first letter of first name + first letter of last name)
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
    <header className="app-header">
      <button
        onClick={(e) => {
          e.preventDefault();
          if (location.pathname !== '/') {
            confirmNavigation(() => navigate('/'));
          }
        }}
        className="logo"
      >
        <Sparkles size={20} className="logo-icon" />
        <h1>Phebe</h1>
      </button>

      <div className="header-container">
        <nav className="header-nav">
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
                className={`nav-link ${isActive ? 'active' : ''}`}
              >
                <Icon size={20} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </div>

      <div className="user-dropdown" ref={dropdownRef}>
        <button
          className="user-button"
          onClick={() => setDropdownOpen(!dropdownOpen)}
          title="Profile"
        >
          <span className="user-initials">{getInitials()}</span>
        </button>

        {dropdownOpen && (
          <div className="dropdown-menu">
            <button onClick={handleLogout} className="dropdown-item">
              <LogOut size={16} />
              <span>Logout</span>
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
