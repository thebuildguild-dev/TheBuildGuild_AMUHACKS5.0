import admin from 'firebase-admin';
import { query } from '../db/pgClient.js';

/**
 * Verify Firebase ID token and upsert user
 * POST /api/auth/verify
 */
export const verifyToken = async (req, res) => {
    try {
        const { idToken } = req.body;

        // Validate input
        if (!idToken) {
            return res.status(400).json({
                error: 'Bad Request',
                message: 'idToken is required',
            });
        }

        // Verify the Firebase ID token
        let decodedToken;
        try {
            decodedToken = await admin.auth().verifyIdToken(idToken);
        } catch (verifyError) {
            console.error('Token verification failed:', verifyError);

            if (verifyError.code === 'auth/id-token-expired') {
                return res.status(401).json({
                    error: 'Unauthorized',
                    message: 'Token has expired',
                });
            }

            if (verifyError.code === 'auth/argument-error') {
                return res.status(400).json({
                    error: 'Bad Request',
                    message: 'Invalid token format',
                });
            }

            return res.status(401).json({
                error: 'Unauthorized',
                message: 'Token verification failed',
            });
        }

        const { uid, email, name, picture } = decodedToken;

        // Upsert user into database
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
        const user = result.rows[0];

        console.log(`User ${uid} authenticated successfully`);

        // Return success response
        return res.status(200).json({
            success: true,
            message: 'Token verified successfully',
            user: {
                id: user.id,
                email: user.email,
                name: user.name,
                createdAt: user.created_at,
            },
        });
    } catch (error) {
        console.error('Auth verification error:', error);

        // Handle database errors
        if (error.code === '23505') { // Unique constraint violation
            return res.status(409).json({
                error: 'Conflict',
                message: 'User already exists',
            });
        }

        if (error.code === '23502') { // Not null constraint violation
            return res.status(400).json({
                error: 'Bad Request',
                message: 'Missing required user information',
            });
        }

        return res.status(500).json({
            error: 'Internal Server Error',
            message: 'Failed to verify token and authenticate user',
        });
    }
};

/**
 * Get current user information
 * GET /api/auth/me
 */
export const getCurrentUser = async (req, res) => {
    try {
        const userId = req.user.uid;

        const selectQuery = `
      SELECT id, email, name, created_at
      FROM users
      WHERE id = $1
    `;

        const result = await query(selectQuery, [userId]);

        if (result.rows.length === 0) {
            return res.status(404).json({
                error: 'Not Found',
                message: 'User not found',
            });
        }

        return res.status(200).json({
            success: true,
            user: result.rows[0],
        });
    } catch (error) {
        console.error('Get current user error:', error);
        return res.status(500).json({
            error: 'Internal Server Error',
            message: 'Failed to retrieve user information',
        });
    }
};

export default {
    verifyToken,
    getCurrentUser,
};
