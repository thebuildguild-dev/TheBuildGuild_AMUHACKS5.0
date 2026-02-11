import admin from 'firebase-admin';
import config from '../config/index.js';

// Initialize Firebase Admin SDK
let firebaseApp;
try {
    if (config.firebaseCredentialsJson) {
        // Parse credentials from JSON string
        const serviceAccount = JSON.parse(config.firebaseCredentialsJson);
        firebaseApp = admin.initializeApp({
            credential: admin.credential.cert(serviceAccount),
            projectId: config.firebaseProjectId,
        });
        console.log('Firebase Admin initialized with credentials JSON');
    } else {
        // Initialize with default credentials (for GCP environments)
        firebaseApp = admin.initializeApp({
            projectId: config.firebaseProjectId,
        });
        console.log('Firebase Admin initialized with default credentials');
    }
} catch (error) {
    console.warn('Firebase Admin initialization skipped:', error.message);
}

/**
 * Authentication middleware
 * Verifies Firebase ID token and attaches user to request
 */
export const authMiddleware = async (req, res, next) => {
    try {
        // Extract token from Authorization header
        const authHeader = req.headers.authorization;

        if (!authHeader || !authHeader.startsWith('Bearer ')) {
            return res.status(401).json({
                error: 'Unauthorized',
                message: 'Missing or invalid Authorization header'
            });
        }

        const idToken = authHeader.split('Bearer ')[1];

        if (!idToken) {
            return res.status(401).json({
                error: 'Unauthorized',
                message: 'No token provided'
            });
        }

        // Verify the ID token
        const decodedToken = await admin.auth().verifyIdToken(idToken);

        // Attach user info to request
        req.user = {
            uid: decodedToken.uid,
            email: decodedToken.email,
            name: decodedToken.name,
        };

        next();
    } catch (error) {
        console.error('Auth middleware error:', error);
        return res.status(401).json({
            error: 'Unauthorized',
            message: 'Invalid or expired token'
        });
    }
};

export default authMiddleware;
