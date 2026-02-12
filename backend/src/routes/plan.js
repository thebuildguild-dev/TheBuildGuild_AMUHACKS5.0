import express from 'express';
import authMiddleware from '../middleware/authMiddleware.js';
import { getPlan, saveRecoveryPlan, getUserPlans, updatePlan } from '../controllers/planController.js';

const router = express.Router();

router.get('/user/history', authMiddleware, getUserPlans);
router.get('/:planId', authMiddleware, getPlan);
router.post('/save', authMiddleware, saveRecoveryPlan);
router.put('/:planId', authMiddleware, updatePlan);

export default router;
