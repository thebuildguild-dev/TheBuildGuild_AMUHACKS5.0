import {
    savePlan,
    formatPlan,
    getPlanById,
    checkAssessmentExists,
    getUserPlansList,
    updatePlanById
} from '../services/planService.js';
import { sendSuccess, sendCreated, sendBadRequest, sendNotFound, handleDatabaseError } from '../utils/response.js';
import log from '../utils/logger.js';

export const getPlan = async (req, res) => {
    try {
        const { planId } = req.params;
        const userId = req.user.uid;

        const planData = await getPlanById(planId, userId);

        if (!planData) {
            return sendNotFound(res, 'Recovery plan not found');
        }

        const formattedPlan = formatPlan(planData);

        return sendSuccess(res, formattedPlan);
    } catch (error) {
        log.error('Get plan error:', error);
        return handleDatabaseError(res, error, 'Failed to retrieve recovery plan');
    }
};

export const saveRecoveryPlan = async (req, res) => {
    try {
        const { assessmentId, plan } = req.body;
        const userId = req.user.uid;

        if (!assessmentId || !plan) {
            return sendBadRequest(res, 'assessmentId and plan are required');
        }

        const assessmentExists = await checkAssessmentExists(assessmentId, userId);

        if (!assessmentExists) {
            return sendNotFound(res, 'Assessment not found');
        }

        const savedPlan = await savePlan(userId, assessmentId, plan);

        log.success(`Recovery plan ${savedPlan.id} saved for user ${userId}`);

        return sendCreated(res, savedPlan, 'Recovery plan saved successfully');
    } catch (error) {
        log.error('Save plan error:', error);
        return handleDatabaseError(res, error, 'Failed to save recovery plan');
    }
};

export const getUserPlans = async (req, res) => {
    try {
        const userId = req.user.uid;

        const plans = await getUserPlansList(userId);

        return sendSuccess(res, plans);
    } catch (error) {
        log.error('Get user plans error:', error);
        return handleDatabaseError(res, error, 'Failed to retrieve recovery plans');
    }
};

export const updatePlan = async (req, res) => {
    try {
        const { planId } = req.params;
        const { plan } = req.body;
        const userId = req.user.uid;

        if (!plan) {
            return sendBadRequest(res, 'Plan data is required');
        }

        const updatedPlan = await updatePlanById(planId, userId, plan);

        if (!updatedPlan) {
            return sendNotFound(res, 'Recovery plan not found');
        }

        log.success(`Recovery plan ${planId} updated for user ${userId}`);

        return sendSuccess(res, updatedPlan, 'Recovery plan updated successfully');
    } catch (error) {
        log.error('Update plan error:', error);
        return handleDatabaseError(res, error, 'Failed to update recovery plan');
    }
};
