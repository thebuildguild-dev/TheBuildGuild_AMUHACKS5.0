import { createContext, useContext, useEffect, useState } from 'react';
import { 
  signInWithPopup, 
  signOut, 
  onAuthStateChanged 
} from 'firebase/auth';
import { auth, googleProvider } from '../config/firebase';
import { authAPI } from '../api/client';
import { toast } from 'react-hot-toast';

const AuthContext = createContext();

export const useAuth = () => useContext(AuthContext);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Sync with backend after Firebase auth
  const syncUserWithBackend = async (firebaseUser) => {
    try {
      const token = await firebaseUser.getIdToken();
      const response = await authAPI.verifyToken(token);
      
      if (response.success && response.data) {
          // Preserve Firebase-specific properties
          return { 
            ...response.data,
            photoURL: firebaseUser.photoURL,
            displayName: firebaseUser.displayName || response.data.name,
            email: firebaseUser.email,
            uid: firebaseUser.uid
          };
      }
      return firebaseUser;
    } catch (error) {
      console.error("Backend sync failed:", error);
      toast.error("Failed to sync user profile");
      return firebaseUser;
    }
  };

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
      if (firebaseUser) {
        // We set loading true only if we weren't already loading 
        // (though initial load is true)
        
        try {
            const syncedUser = await syncUserWithBackend(firebaseUser);
            setUser(syncedUser);
        } catch (err) {
            console.error(err);
            setUser(firebaseUser);
        }
      } else {
        setUser(null);
      }
      setLoading(false);
    });
    return unsubscribe;
  }, []);

  const login = async () => {
    try {
      const result = await signInWithPopup(auth, googleProvider);
      // Backend sync happens in onAuthStateChanged
      toast.success("Welcome.");
      return result.user;
    } catch (error) {
      console.error(error);
      toast.error("Login failed");
      throw error;
    }
  };

  const logout = async () => {
    try {
      await signOut(auth);
      toast.success("Session terminated.");
    } catch (error) {
      console.error(error);
      toast.error("Logout failed");
    }
  };

  const value = {
    user,
    loading,
    login,
    logout
  };

  return (
    <AuthContext.Provider value={value}>
      {!loading && children}
    </AuthContext.Provider>
  );
};
