import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { LogOut, User, LayoutDashboard, BrainCircuit, UploadCloud, History } from 'lucide-react';
import './Header.css';

const Header = () => {
  const { user, logout } = useAuth();
  const location = useLocation();
  
  const isActive = (path) => location.pathname === path ? 'active-link' : '';

  return (
    <header className="app-header">
      <div className="container header-content">
        <Link to="/dashboard" className="logo">
          EXAM<span className="logo-accent">INTEL</span>
        </Link>
        
        <nav className="header-nav">
          <Link to="/dashboard" className={`nav-link ${isActive('/dashboard')}`} title="Dashboard">
            <LayoutDashboard size={20} />
            <span className="nav-label">Dashboard</span>
          </Link>
          <Link to="/assessment" className={`nav-link ${isActive('/assessment')}`} title="New Assessment">
            <BrainCircuit size={20} />
            <span className="nav-label">Assess</span>
          </Link>
          <Link to="/history" className={`nav-link ${isActive('/history')}`} title="History">
            <History size={20} />
            <span className="nav-label">History</span>
          </Link>
          <Link to="/upload-pyq" className={`nav-link ${isActive('/upload-pyq')}`} title="Upload PYQs">
            <UploadCloud size={20} />
            <span className="nav-label">Upload</span>
          </Link>
          
          <div className="nav-divider"></div>
          
          <Link to="/profile" className={`nav-link profile-link ${isActive('/profile')}`}>
            {user?.photoURL ? (
                <img src={user.photoURL} alt="Profile" className="profile-img" />
            ) : (
                <User size={20} />
            )}
            <span className="nav-label user-name">{user?.displayName?.split(' ')[0] || 'User'}</span>
          </Link>
          
          <button onClick={logout} className="header-logout-btn" title="Logout">
            <LogOut size={20} />
          </button>
        </nav>
      </div>
    </header>
  );
};

export default Header;
