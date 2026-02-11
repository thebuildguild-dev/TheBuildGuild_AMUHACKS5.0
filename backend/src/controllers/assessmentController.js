import { query } from '../db/pgClient.js';
import { generatePlan } from '../services/planService.js';

/**
 * POST /api/assessment/submit
 * Submit assessment answers and generate recovery plan
 */
export const submitAssessment = async (req, res) => {
    try {
        const { answers } = req.body;
        const userId = req.user.uid;

        // Validate assessment payload
        if (!answers || typeof answers !== 'object') {
            return res.status(400).json({
                error: 'Bad Request',
                message: 'Assessment answers are required',
            });
        }

        // Validate we have 6-7 questions answered
        const answerKeys = Object.keys(answers);
        if (answerKeys.length < 6 || answerKeys.length > 7) {
            return res.status(400).json({
                error: 'Bad Request',
                message: 'Assessment must contain 6-7 questions',
            });
        }

        // Compute basic skill-gap vector
        // Simple scoring: each answer has confidence (1-5) and correctness
        const gapVector = computeSkillGap(answers);

        // Save assessment to database
        const insertQuery = `
      INSERT INTO assessments (id, user_id, payload, gap_vector, created_at)
      VALUES (gen_random_uuid(), $1, $2, $3, NOW())
      RETURNING id, user_id, payload, gap_vector, created_at
    `;

        const assessmentResult = await query(insertQuery, [
            userId,
            JSON.stringify(answers),
            JSON.stringify(gapVector),
        ]);

        const assessment = assessmentResult.rows[0];

        console.log(`Assessment ${assessment.id} saved for user ${userId}`);

        // Generate recovery plan
        try {
            const plan = await generatePlan(userId, {
                assessmentId: assessment.id,
                answers,
                gapVector,
            });

            return res.status(200).json({
                success: true,
                message: 'Assessment submitted and plan generated',
                data: {
                    assessmentId: assessment.id,
                    plan,
                },
            });
        } catch (planError) {
            console.error('Plan generation error:', planError);

            // Assessment saved but plan generation failed
            // Return assessment ID so client can retry plan generation
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
        console.error('Assessment submission error:', error);
        return res.status(500).json({
            error: 'Internal Server Error',
            message: 'Failed to submit assessment',
        });
    }
};

/**
 * GET /api/assessment/:id
 * Retrieve a specific assessment
 */
export const getAssessment = async (req, res) => {
    try {
        const { id } = req.params;
        const userId = req.user.uid;

        const selectQuery = `
      SELECT id, user_id, payload, gap_vector, created_at
      FROM assessments
      WHERE id = $1 AND user_id = $2
    `;

        const result = await query(selectQuery, [id, userId]);

        if (result.rows.length === 0) {
            return res.status(404).json({
                error: 'Not Found',
                message: 'Assessment not found',
            });
        }

        return res.status(200).json({
            success: true,
            data: result.rows[0],
        });
    } catch (error) {
        console.error('Get assessment error:', error);
        return res.status(500).json({
            error: 'Internal Server Error',
            message: 'Failed to retrieve assessment',
        });
    }
};

/**
 * GET /api/assessment/user/history
 * Get all assessments for current user
 */
export const getUserAssessments = async (req, res) => {
    try {
        const userId = req.user.uid;

        const selectQuery = `
      SELECT id, payload, gap_vector, created_at
      FROM assessments
      WHERE user_id = $1
      ORDER BY created_at DESC
      LIMIT 10
    `;

        const result = await query(selectQuery, [userId]);

        return res.status(200).json({
            success: true,
            data: result.rows,
        });
    } catch (error) {
        console.error('Get user assessments error:', error);
        return res.status(500).json({
            error: 'Internal Server Error',
            message: 'Failed to retrieve assessments',
        });
    }
};

/**
 * Compute skill gap vector from assessment answers
 * @param {Object} answers - Assessment answers object
 * @returns {Object} Skill gap vector with subject/topic scores
 */
function computeSkillGap(answers) {
    const gapVector = {
        subjects: {},
        overallConfidence: 0,
        weakAreas: [],
    };

    let totalConfidence = 0;
    let count = 0;

    for (const [questionId, answer] of Object.entries(answers)) {
        const {
            subject,
            topic,
            confidence = 3,
            correctness,
            timeSpent,
        } = answer;

        // Initialize subject if not exists
        if (!gapVector.subjects[subject]) {
            gapVector.subjects[subject] = {
                topics: {},
                avgConfidence: 0,
                needsWork: false,
            };
        }

        // Calculate gap score (lower confidence = higher gap)
        const gapScore = 5 - confidence;

        // Track topic-level gaps
        if (!gapVector.subjects[subject].topics[topic]) {
            gapVector.subjects[subject].topics[topic] = {
                gapScore,
                confidence,
                correctness,
                questionCount: 1,
            };
        } else {
            const t = gapVector.subjects[subject].topics[topic];
            t.gapScore = (t.gapScore + gapScore) / 2;
            t.confidence = (t.confidence + confidence) / 2;
            t.questionCount++;
        }

        totalConfidence += confidence;
        count++;

        // Mark as weak area if confidence < 3
        if (confidence < 3) {
            gapVector.weakAreas.push({ subject, topic, confidence });
        }
    }

    // Calculate overall confidence
    gapVector.overallConfidence = count > 0 ? totalConfidence / count : 0;

    // Mark subjects that need work
    for (const subject of Object.keys(gapVector.subjects)) {
        const topics = Object.values(gapVector.subjects[subject].topics);
        const avgConf = topics.reduce((sum, t) => sum + t.confidence, 0) / topics.length;
        gapVector.subjects[subject].avgConfidence = avgConf;
        gapVector.subjects[subject].needsWork = avgConf < 3;
    }

    return gapVector;
}
