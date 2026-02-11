import express from 'express';
import authMiddleware from '../middleware/authMiddleware.js';
import {
    getPlan,
    saveRecoveryPlan,
    getUserPlans,
    updatePlan,
} from '../controllers/planController.js';
import { query } from '../db/pgClient.js';

const router = express.Router();

/**
 * GET /api/plan/:planId
 * Get a single recovery plan by ID
 * Protected route - requires authentication
 */
router.get('/:planId', authMiddleware, async (req, res) => {
    try {
        const { planId } = req.params;

        // Validate planId format (UUID)
        const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
        if (!uuidRegex.test(planId)) {
            return res.status(400).json({
                error: 'Bad Request',
                message: 'Invalid plan ID format',
            });
        }

        // Call controller
        return await getPlan(req, res);
    } catch (error) {
        console.error('Get plan error:', error);
        return res.status(500).json({
            error: 'Internal Server Error',
            message: 'Failed to retrieve recovery plan',
        });
    }
});

/**
 * GET /api/plan/user/all
 * Get all recovery plans for logged-in user
 * Protected route - requires authentication
 */
router.get('/user/all', authMiddleware, async (req, res) => {
    return await getUserPlans(req, res);
});

/**
 * POST /api/plan/save
 * Save a new recovery plan to database
 * Protected route - requires authentication
 */
router.post('/save', authMiddleware, async (req, res) => {
    try {
        const { assessmentId, plan } = req.body;

        // Validate required fields
        if (!assessmentId) {
            return res.status(400).json({
                error: 'Bad Request',
                message: 'assessmentId is required',
            });
        }

        if (!plan || typeof plan !== 'object') {
            return res.status(400).json({
                error: 'Bad Request',
                message: 'plan must be a valid object',
            });
        }

        // Validate assessmentId format (UUID)
        const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
        if (!uuidRegex.test(assessmentId)) {
            return res.status(400).json({
                error: 'Bad Request',
                message: 'Invalid assessment ID format',
            });
        }

        // Call controller
        return await saveRecoveryPlan(req, res);
    } catch (error) {
        console.error('Save plan error:', error);
        return res.status(500).json({
            error: 'Internal Server Error',
            message: 'Failed to save recovery plan',
        });
    }
});

/**
 * PUT /api/plan/:planId
 * Update an existing recovery plan
 * Protected route - requires authentication
 */
router.put('/:planId', authMiddleware, async (req, res) => {
    try {
        const { planId } = req.params;

        // Validate planId format (UUID)
        const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
        if (!uuidRegex.test(planId)) {
            return res.status(400).json({
                error: 'Bad Request',
                message: 'Invalid plan ID format',
            });
        }

        const { plan } = req.body;
        if (!plan || typeof plan !== 'object') {
            return res.status(400).json({
                error: 'Bad Request',
                message: 'plan must be a valid object',
            });
        }

        // Call controller
        return await updatePlan(req, res);
    } catch (error) {
        console.error('Update plan error:', error);
        return res.status(500).json({
            error: 'Internal Server Error',
            message: 'Failed to update recovery plan',
        });
    }
});

/**
 * DELETE /api/plan/:planId
 * Delete a recovery plan owned by the user
 * Protected route - requires authentication
 */
router.delete('/:planId', authMiddleware, async (req, res) => {
    try {
        const { planId } = req.params;
        const userId = req.user.uid;

        // Validate planId format (UUID)
        const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
        if (!uuidRegex.test(planId)) {
            return res.status(400).json({
                error: 'Bad Request',
                message: 'Invalid plan ID format',
            });
        }

        // Delete plan
        const deleteQuery = `
      DELETE FROM recovery_plans
      WHERE id = $1 AND user_id = $2
      RETURNING id
    `;

        const result = await query(deleteQuery, [planId, userId]);

        if (result.rows.length === 0) {
            return res.status(404).json({
                error: 'Not Found',
                message: 'Recovery plan not found or unauthorized',
            });
        }

        console.log(`Recovery plan ${planId} deleted for user ${userId}`);

        return res.status(200).json({
            success: true,
            message: 'Recovery plan deleted successfully',
            data: {
                deletedPlanId: result.rows[0].id,
            },
        });
    } catch (error) {
        console.error('Delete plan error:', error);
        return res.status(500).json({
            error: 'Internal Server Error',
            message: 'Failed to delete recovery plan',
        });
    }
});

export default router;
