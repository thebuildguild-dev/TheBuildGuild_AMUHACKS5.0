import express from 'express';
import admin from 'firebase-admin';
import { query } from '../db/pgClient.js';

const router = express.Router();

/**
 * POST /api/auth/verify
 * Verify Firebase ID token and upsert user
 */
router.post('/verify', async (req, res) => {
    try {
        const { idToken } = req.body;

        if (!idToken) {
            return res.status(400).json({
                error: 'Bad Request',
                message: 'idToken is required'
            });
        }

        // Verify the ID token with Firebase
        const decodedToken = await admin.auth().verifyIdToken(idToken);

        const { uid, email, name } = decodedToken;

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

        if (error.code === 'auth/id-token-expired') {
            return res.status(401).json({
                error: 'Unauthorized',
                message: 'Token has expired'
            });
        }

        if (error.code === 'auth/argument-error') {
            return res.status(400).json({
                error: 'Bad Request',
                message: 'Invalid token format'
            });
        }

        return res.status(401).json({
            error: 'Unauthorized',
            message: 'Token verification failed'
        });
    }
});

export default router;
