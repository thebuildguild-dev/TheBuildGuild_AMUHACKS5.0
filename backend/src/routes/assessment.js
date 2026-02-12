import express from 'express';
import authMiddleware from '../middleware/authMiddleware.js';
import { submitAssessment, getAssessment, getUserAssessments } from '../controllers/assessmentController.js';

const router = express.Router();

router.post('/submit', authMiddleware, submitAssessment);
router.get('/user/history', authMiddleware, getUserAssessments);
router.get('/:id', authMiddleware, getAssessment);

export default router;
