import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { AuthProvider, useAuth } from './context/AuthContext';

// Pages
import Landing from './pages/Landing';
import Dashboard from './pages/Dashboard';
import Profile from './pages/Profile';
import Assessment from './pages/Assessment';
import UploadPYQ from './pages/UploadPYQ';
import NotFound from './pages/NotFound';
import Plan from './pages/Plan';
import History from './pages/History';
import Footer from './components/Footer';

// Protected Route Component
const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();
  
  if (loading) return (
    <div style={{ 
        height: '100vh', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        background: 'var(--bg-deep)',
        color: 'var(--accent-primary)',
        fontFamily: 'var(--font-display)',
        fontSize: '2rem'
    }}>
        INITIALIZING SYSTEM...
    </div>
  );
  
  if (!user) {
    return <Navigate to="/" replace />;
  }

  return children;
};

function App() {
  return (
    <AuthProvider>
        <Router>
            <div className="app-container">
                <Toaster 
                    position="bottom-right"
                    toastOptions={{
                        style: {
                            background: '#0a0a0a',
                            color: '#fff',
                            border: '1px solid #333',
                            borderRadius: '0px',
                            fontFamily: 'var(--font-body)',
                        },
                        success: {
                            style: {
                                border: '1px solid var(--accent-primary)',
                                color: 'var(--accent-primary)',
                            },
                            iconTheme: {
                                primary: 'var(--accent-primary)',
                                secondary: '#000',
                            },
                        }
                    }}
                />
                
                <Routes>
                    <Route path="/" element={<Landing />} />
                    
                    <Route path="/dashboard" element={
                        <ProtectedRoute>
                            <Dashboard />
                        </ProtectedRoute>
                    } />
                    
                    <Route path="/profile" element={
                        <ProtectedRoute>
                            <Profile />
                        </ProtectedRoute>
                    } />
                    
                    <Route path="/assessment" element={
                        <ProtectedRoute>
                            <Assessment />
                        </ProtectedRoute>
                    } />
                    
                    <Route path="/upload-pyq" element={
                        <ProtectedRoute>
                            <UploadPYQ />
                        </ProtectedRoute>
                    } />

                    <Route path="/plan/:planId" element={
                        <ProtectedRoute>
                            <Plan />
                        </ProtectedRoute>
                    } />

                    <Route path="/history" element={
                        <ProtectedRoute>
                            <History />
                        </ProtectedRoute>
                    } />

                    <Route path="*" element={<NotFound />} />
                </Routes>
                <Footer />
            </div>
        </Router>
    </AuthProvider>
  );
}

export default App;
