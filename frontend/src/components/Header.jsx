import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Home, Settings, User, LogOut } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import './Header.css';

export default function Header() {
  const location = useLocation();
  const navigate = useNavigate();
  const { logout } = useAuth();

  const navItems = [
    { path: '/', icon: Home, label: 'Home' },
    { path: '/settings', icon: Settings, label: 'Settings' },
  ];

  const handleLogout = () => {
    logout();
    navigate('/signin');
  };

  return (
    <header className="app-header">
      <div className="header-container">
        <div className="logo">
          <h1>Phebe</h1>
        </div>

        <div className="header-right">
          <nav className="header-nav">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`nav-link ${isActive ? 'active' : ''}`}
                >
                  <Icon size={20} />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>

          <div className="header-actions">
            <button className="user-button" title="Profile">
              <User size={20} />
            </button>
            <button className="logout-button" onClick={handleLogout} title="Logout">
              <LogOut size={20} />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
