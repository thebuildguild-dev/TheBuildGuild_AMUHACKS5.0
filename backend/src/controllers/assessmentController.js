import {
    saveAssessment,
    getAssessmentById,
    getAssessmentsByUser
} from '../services/assessmentService.js';
import { generatePlan, savePlan } from '../services/planService.js';
import { sendPlanGeneratedEmail } from '../services/emailService.js';
import { sendSuccess, sendBadRequest, sendNotFound, handleDatabaseError } from '../utils/response.js';
import log from '../utils/logger.js';

export const submitAssessment = async (req, res) => {
    try {
        const { examDate, subject, topics, stressLevel, syllabusCoverage, additionalNotes } = req.body;
        const userId = req.user.uid;

        if (!examDate || !subject) {
            return sendBadRequest(res, 'Exam date and subject are required');
        }

        if (new Date(examDate) < new Date()) {
            return sendBadRequest(res, 'Exam date must be in the future');
        }

        const assessmentData = {
            examDate,
            subject,
            topics: topics || [],
            stressLevel: parseInt(stressLevel) || 5,
            syllabusCoverage: parseInt(syllabusCoverage) || 50,
            additionalNotes: additionalNotes || ''
        };

        const assessment = await saveAssessment(userId, assessmentData);
        log.success(`Assessment ${assessment.id} saved for user ${userId}`);

        try {
            const plan = await generatePlan(userId, assessmentData);
            const savedPlan = await savePlan(userId, assessment.id, plan);

            // Send email notification
            if (req.user.email) {
                await sendPlanGeneratedEmail(req.user.email, plan, assessmentData, savedPlan.id);
            }

            return sendSuccess(res, {
                assessmentId: assessment.id,
                plan: {
                    id: savedPlan.id,
                    ...plan
                }
            }, 'Assessment submitted and AI recovery plan generated');
        } catch (planError) {
            log.error('Plan generation error:', planError.message);

            return res.status(202).json({
                success: true,
                message: 'Assessment saved, but plan generation failed. Please try again.',
                data: {
                    assessmentId: assessment.id,
                    status: 'pending',
                    error: planError.message
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
