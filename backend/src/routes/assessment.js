import express from 'express';
import authMiddleware from '../middleware/authMiddleware.js';
import {
    submitAssessment,
    getAssessment,
    getUserAssessments,
} from '../controllers/assessmentController.js';

const router = express.Router();

/**
 * POST /api/assessment/submit
 * Submit student assessment and generate recovery plan
 * Protected route - requires authentication
 */
router.post('/submit', authMiddleware, async (req, res) => {
    try {
        const { subjects, understanding_gaps, stress_level, current_coverage, answers } = req.body;

        // Validate request body
        if (!subjects && !answers) {
            return res.status(400).json({
                error: 'Bad Request',
                message: 'Assessment data is required (subjects or answers)',
            });
        }

        // If new format with subjects array
        if (subjects && Array.isArray(subjects)) {
            // Validate subjects array
            for (const subject of subjects) {
                if (!subject.name) {
                    return res.status(400).json({
                        error: 'Bad Request',
                        message: 'Each subject must have a name',
                    });
                }
            }

            // Validate understanding_gaps if provided
            if (understanding_gaps && typeof understanding_gaps !== 'object') {
                return res.status(400).json({
                    error: 'Bad Request',
                    message: 'understanding_gaps must be an object',
                });
            }

            // Validate stress_level range
            if (stress_level !== undefined && (stress_level < 0 || stress_level > 1)) {
                return res.status(400).json({
                    error: 'Bad Request',
                    message: 'stress_level must be between 0 and 1',
                });
            }

            // Validate current_coverage range
            if (current_coverage !== undefined && (current_coverage < 0 || current_coverage > 1)) {
                return res.status(400).json({
                    error: 'Bad Request',
                    message: 'current_coverage must be between 0 and 1',
                });
            }

            // Transform to expected format for controller
            req.body = {
                answers: transformToAnswersFormat(subjects, understanding_gaps, stress_level),
                metadata: {
                    subjects,
                    stress_level,
                    current_coverage,
                },
            };
        }

        // Call controller
        return await submitAssessment(req, res);
    } catch (error) {
        console.error('Assessment submission error:', error);
        return res.status(500).json({
            error: 'Internal Server Error',
            message: 'Failed to process assessment',
        });
    }
});

/**
 * GET /api/assessment/history
 * Get all past assessments for logged-in user
 * Protected route - requires authentication
 */
router.get('/history', authMiddleware, async (req, res) => {
    return await getUserAssessments(req, res);
});

/**
 * GET /api/assessment/:id
 * Get specific assessment by ID
 * Protected route - requires authentication
 */
router.get('/:id', authMiddleware, async (req, res) => {
    return await getAssessment(req, res);
});

/**
 * Helper function to transform subjects format to answers format
 * @param {Array} subjects - Array of subject objects
 * @param {Object} understanding_gaps - Topic gaps (0-10 scale)
 * @param {number} stress_level - Stress level (0-1)
 * @returns {Object} Transformed answers object
 */
function transformToAnswersFormat(subjects, understanding_gaps = {}, stress_level = 0.5) {
    const answers = {};
    let questionIndex = 1;

    for (const subject of subjects) {
        const subjectName = subject.name;
        const availableHours = subject.available_hours_per_day || 2;
        const examDate = subject.exam_date;

        // Find related topics from understanding_gaps
        const relatedTopics = Object.entries(understanding_gaps).filter(([topic]) =>
            topic.toLowerCase().includes(subjectName.toLowerCase()) ||
            subjectName.toLowerCase().includes(topic.toLowerCase())
        );

        if (relatedTopics.length === 0) {
            // Create a general question for this subject
            answers[`q${questionIndex}`] = {
                subject: subjectName,
                topic: 'General',
                confidence: Math.max(1, 5 - Math.floor(stress_level * 4)), // 1-5 scale
                correctness: null,
                timeSpent: null,
                metadata: {
                    availableHours,
                    examDate,
                },
            };
            questionIndex++;
        } else {
            // Create questions for each topic
            for (const [topic, gapScore] of relatedTopics) {
                // Transform gap score from 0-10 to confidence 1-5 (inverted)
                const confidence = Math.max(1, Math.min(5, 5 - Math.floor(gapScore / 2)));

                answers[`q${questionIndex}`] = {
                    subject: subjectName,
                    topic,
                    confidence,
                    correctness: gapScore < 5 ? 'correct' : 'incorrect',
                    timeSpent: null,
                    metadata: {
                        availableHours,
                        examDate,
                        originalGapScore: gapScore,
                    },
                };
                questionIndex++;
            }
        }
    }

    return answers;
}

export default router;
