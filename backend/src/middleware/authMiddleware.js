import admin from 'firebase-admin';
import config from '../config/index.js';
import { sendUnauthorized } from '../utils/response.js';
import log from '../utils/logger.js';

let firebaseApp;
try {
    if (config.firebaseCredentialsJson) {
        const serviceAccount = JSON.parse(config.firebaseCredentialsJson);
        firebaseApp = admin.initializeApp({
            credential: admin.credential.cert(serviceAccount),
            projectId: config.firebaseProjectId,
        });
        log.success('Firebase Admin initialized with credentials JSON');
    } else {
        firebaseApp = admin.initializeApp({
            projectId: config.firebaseProjectId,
        });
        log.success('Firebase Admin initialized with default credentials');
    }
} catch (error) {
    log.warn('Firebase Admin initialization skipped:', error.message);
}

export const authMiddleware = async (req, res, next) => {
    try {
        const authHeader = req.headers.authorization;

        if (!authHeader || !authHeader.startsWith('Bearer ')) {
            return sendUnauthorized(res, 'Missing or invalid Authorization header');
        }

        const idToken = authHeader.split('Bearer ')[1];

        if (!idToken) {
            return sendUnauthorized(res, 'No token provided');
        }

        const decodedToken = await admin.auth().verifyIdToken(idToken);

        req.user = {
            uid: decodedToken.uid,
            email: decodedToken.email,
            name: decodedToken.name,
        };

        next();
    } catch (error) {
        log.error('Auth middleware error:', error.code);
        return sendUnauthorized(res, 'Invalid or expired token');
    }
};

export default authMiddleware;
