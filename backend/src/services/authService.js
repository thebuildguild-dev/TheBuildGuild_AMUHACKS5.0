import admin from 'firebase-admin';
import { query } from '../db/pgClient.js';
import log from '../utils/logger.js';

export const verifyFirebaseToken = async (idToken) => {
    try {
        const decodedToken = await admin.auth().verifyIdToken(idToken);
        return { success: true, decodedToken };
    } catch (error) {
        log.error('Token verification failed:', error.code);
        return {
            success: false,
            error: {
                code: error.code,
                message: getTokenErrorMessage(error.code)
            }
        };
    }
};

const getTokenErrorMessage = (code) => {
    switch (code) {
        case 'auth/id-token-expired':
            return 'Token has expired';
        case 'auth/argument-error':
            return 'Invalid token format';
        default:
            return 'Token verification failed';
    }
};

export const upsertUser = async (uid, email, name) => {
    const upsertQuery = `
        INSERT INTO users (id, email, name, created_at)
        VALUES ($1, $2, $3, NOW())
        ON CONFLICT (id) 
        DO UPDATE SET 
            email = EXCLUDED.email,
            name = EXCLUDED.name
        RETURNING id, email, name, created_at
    `;

    const result = await query(upsertQuery, [uid, email, name || null]);
    return result.rows[0];
};

export const getUserById = async (userId) => {
    const selectQuery = `
        SELECT id, email, name, created_at
        FROM users
        WHERE id = $1
    `;

    const result = await query(selectQuery, [userId]);
    return result.rows[0] || null;
};
