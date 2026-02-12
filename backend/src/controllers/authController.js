import { verifyFirebaseToken, upsertUser, getUserById } from '../services/authService.js';
import { sendSuccess, sendBadRequest, sendUnauthorized, sendNotFound, handleDatabaseError } from '../utils/response.js';
import log from '../utils/logger.js';

export const verifyToken = async (req, res) => {
    try {
        const { idToken } = req.body;

        if (!idToken) {
            return sendBadRequest(res, 'idToken is required');
        }

        const verificationResult = await verifyFirebaseToken(idToken);

        if (!verificationResult.success) {
            const { code, message } = verificationResult.error;

            if (code === 'auth/id-token-expired') {
                return sendUnauthorized(res, message);
            }

            if (code === 'auth/argument-error') {
                return sendBadRequest(res, message);
            }

            return sendUnauthorized(res, message);
        }

        const { uid, email, name } = verificationResult.decodedToken;

        const user = await upsertUser(uid, email, name);

        log.success(`User ${uid} authenticated`);

        return sendSuccess(res, {
            id: user.id,
            email: user.email,
            name: user.name,
            createdAt: user.created_at,
        }, 'Token verified successfully');
    } catch (error) {
        return handleDatabaseError(res, error, 'Failed to verify token');
    }
};

export const getCurrentUser = async (req, res) => {
    try {
        const userId = req.user.uid;

        const user = await getUserById(userId);

        if (!user) {
            return sendNotFound(res, 'User not found');
        }

        return sendSuccess(res, user);
    } catch (error) {
        log.error('Get current user error:', error);
        return handleDatabaseError(res, error, 'Failed to retrieve user information');
    }
};
