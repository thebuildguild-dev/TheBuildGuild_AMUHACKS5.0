import express from 'express';
import authMiddleware from '../middleware/authMiddleware.js';
import { authRateLimiter } from '../middleware/rateLimitMiddleware.js';
import { verifyToken, getCurrentUser } from '../controllers/authController.js';

const router = express.Router();

router.post('/verify', authRateLimiter, verifyToken);
router.get('/me', authMiddleware, getCurrentUser);

export default router;
