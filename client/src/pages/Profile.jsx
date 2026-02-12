import Header from '../components/Header';
import { useAuth } from '../context/AuthContext';
import './Profile.css';

const Profile = () => {
    const { user, logout } = useAuth();
    return (
        <div className="profile-page container">
            <Header />
            <div className="profile-content">
                <img 
                    src={user?.photoURL} 
                    alt="Profile" 
                    className="profile-avatar"
                />
                <h1 className="profile-name">
                    {user?.displayName}
                </h1>
                <p className="profile-email">{user?.email}</p>
                
                <button 
                    onClick={logout}
                    className="logout-btn"
                >
                    TERMINATE SESSION
                </button>
            </div>
        </div>
    );
};

export default Profile;
