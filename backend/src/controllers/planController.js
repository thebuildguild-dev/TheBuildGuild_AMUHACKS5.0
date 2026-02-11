import { query } from '../db/pgClient.js';
import { savePlan, formatPlan } from '../services/planService.js';

/**
 * GET /api/plan/:planId
 * Retrieve a recovery plan by ID
 */
export const getPlan = async (req, res) => {
    try {
        const { planId } = req.params;
        const userId = req.user.uid;

        const selectQuery = `
      SELECT id, user_id, assessment_id, plan, created_at, updated_at
      FROM recovery_plans
      WHERE id = $1 AND user_id = $2
    `;

        const result = await query(selectQuery, [planId, userId]);

        if (result.rows.length === 0) {
            return res.status(404).json({
                error: 'Not Found',
                message: 'Recovery plan not found',
            });
        }

        const planData = result.rows[0];

        // Format plan for frontend consumption
        const formattedPlan = formatPlan(planData);

        return res.status(200).json({
            success: true,
            data: formattedPlan,
        });
    } catch (error) {
        console.error('Get plan error:', error);
        return res.status(500).json({
            error: 'Internal Server Error',
            message: 'Failed to retrieve recovery plan',
        });
    }
};

/**
 * POST /api/plan/save
 * Save a recovery plan to the database
 */
export const saveRecoveryPlan = async (req, res) => {
    try {
        const { assessmentId, plan } = req.body;
        const userId = req.user.uid;

        // Validate input
        if (!assessmentId || !plan) {
            return res.status(400).json({
                error: 'Bad Request',
                message: 'assessmentId and plan are required',
            });
        }

        // Verify assessment belongs to user
        const assessmentCheck = await query(
            'SELECT id FROM assessments WHERE id = $1 AND user_id = $2',
            [assessmentId, userId]
        );

        if (assessmentCheck.rows.length === 0) {
            return res.status(404).json({
                error: 'Not Found',
                message: 'Assessment not found',
            });
        }

        // Save plan using service
        const savedPlan = await savePlan(userId, assessmentId, plan);

        console.log(`Recovery plan ${savedPlan.id} saved for user ${userId}`);

        return res.status(201).json({
            success: true,
            message: 'Recovery plan saved successfully',
            data: savedPlan,
        });
    } catch (error) {
        console.error('Save plan error:', error);
        return res.status(500).json({
            error: 'Internal Server Error',
            message: 'Failed to save recovery plan',
        });
    }
};

/**
 * GET /api/plan/user/history
 * Get all recovery plans for current user
 */
export const getUserPlans = async (req, res) => {
    try {
        const userId = req.user.uid;

        const selectQuery = `
      SELECT 
        rp.id, 
        rp.assessment_id, 
        rp.plan, 
        rp.created_at,
        rp.updated_at,
        a.payload as assessment_payload
      FROM recovery_plans rp
      LEFT JOIN assessments a ON rp.assessment_id = a.id
      WHERE rp.user_id = $1
      ORDER BY rp.created_at DESC
      LIMIT 20
    `;

        const result = await query(selectQuery, [userId]);

        const formattedPlans = result.rows.map(row => ({
            id: row.id,
            assessmentId: row.assessment_id,
            plan: row.plan,
            createdAt: row.created_at,
            updatedAt: row.updated_at,
            assessmentSummary: row.assessment_payload ? {
                subjects: Object.keys(JSON.parse(row.assessment_payload)),
                questionCount: Object.keys(JSON.parse(row.assessment_payload)).length,
            } : null,
        }));

        return res.status(200).json({
            success: true,
            data: formattedPlans,
        });
    } catch (error) {
        console.error('Get user plans error:', error);
        return res.status(500).json({
            error: 'Internal Server Error',
            message: 'Failed to retrieve recovery plans',
        });
    }
};

/**
 * PUT /api/plan/:planId
 * Update an existing recovery plan
 */
export const updatePlan = async (req, res) => {
    try {
        const { planId } = req.params;
        const { plan } = req.body;
        const userId = req.user.uid;

        if (!plan) {
            return res.status(400).json({
                error: 'Bad Request',
                message: 'Plan data is required',
            });
        }

        const updateQuery = `
      UPDATE recovery_plans
      SET plan = $1, updated_at = NOW()
      WHERE id = $2 AND user_id = $3
      RETURNING id, user_id, assessment_id, plan, created_at, updated_at
    `;

        const result = await query(updateQuery, [
            JSON.stringify(plan),
            planId,
            userId,
        ]);

        if (result.rows.length === 0) {
            return res.status(404).json({
                error: 'Not Found',
                message: 'Recovery plan not found',
            });
        }

        console.log(`Recovery plan ${planId} updated for user ${userId}`);

        return res.status(200).json({
            success: true,
            message: 'Recovery plan updated successfully',
            data: result.rows[0],
        });
    } catch (error) {
        console.error('Update plan error:', error);
        return res.status(500).json({
            error: 'Internal Server Error',
            message: 'Failed to update recovery plan',
        });
    }
};
