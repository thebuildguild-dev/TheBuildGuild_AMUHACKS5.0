import express from 'express';
import authMiddleware from '../middleware/authMiddleware.js';
import { verifyToken, getCurrentUser } from '../controllers/authController.js';

const router = express.Router();

router.post('/verify', verifyToken);
router.get('/me', authMiddleware, getCurrentUser);

export default router;
