import {
    validateAssessmentAnswers,
    computeSkillGap,
    saveAssessment,
    getAssessmentById,
    getAssessmentsByUser
} from '../services/assessmentService.js';
import { generatePlan } from '../services/planService.js';
import { sendSuccess, sendBadRequest, sendNotFound, handleDatabaseError } from '../utils/response.js';
import log from '../utils/logger.js';

export const submitAssessment = async (req, res) => {
    try {
        const { answers } = req.body;
        const userId = req.user.uid;

        const validation = validateAssessmentAnswers(answers);
        if (!validation.valid) {
            return sendBadRequest(res, validation.message);
        }

        const gapVector = computeSkillGap(answers);

        const assessment = await saveAssessment(userId, answers, gapVector);

        log.success(`Assessment ${assessment.id} saved for user ${userId}`);

        try {
            const plan = await generatePlan(userId, {
                assessmentId: assessment.id,
                answers,
                gapVector,
            });

            return sendSuccess(res, {
                assessmentId: assessment.id,
                plan,
            }, 'Assessment submitted and plan generated');
        } catch (planError) {
            log.error('Plan generation error:', planError.message);

            return res.status(202).json({
                success: true,
                message: 'Assessment saved, plan generation in progress',
                data: {
                    assessmentId: assessment.id,
                    status: 'pending',
                },
            });
        }
    } catch (error) {
        log.error('Assessment submission error:', error);
        return handleDatabaseError(res, error, 'Failed to submit assessment');
    }
};

export const getAssessment = async (req, res) => {
    try {
        const { id } = req.params;
        const userId = req.user.uid;

        const assessment = await getAssessmentById(id, userId);

        if (!assessment) {
            return sendNotFound(res, 'Assessment not found');
        }

        return sendSuccess(res, assessment);
    } catch (error) {
        log.error('Get assessment error:', error);
        return handleDatabaseError(res, error, 'Failed to retrieve assessment');
    }
};

export const getUserAssessments = async (req, res) => {
    try {
        const userId = req.user.uid;

        const assessments = await getAssessmentsByUser(userId);

        return sendSuccess(res, assessments);
    } catch (error) {
        log.error('Get user assessments error:', error);
        return handleDatabaseError(res, error, 'Failed to retrieve assessments');
    }
};
