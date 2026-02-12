import { query } from '../db/pgClient.js';

export const computeSkillGap = (answers) => {
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

        if (!gapVector.subjects[subject]) {
            gapVector.subjects[subject] = {
                topics: {},
                avgConfidence: 0,
                needsWork: false,
            };
        }

        const gapScore = 5 - confidence;

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

        if (confidence < 3) {
            gapVector.weakAreas.push({ subject, topic, confidence });
        }
    }

    gapVector.overallConfidence = count > 0 ? totalConfidence / count : 0;

    for (const subject of Object.keys(gapVector.subjects)) {
        const topics = Object.values(gapVector.subjects[subject].topics);
        const avgConf = topics.reduce((sum, t) => sum + t.confidence, 0) / topics.length;
        gapVector.subjects[subject].avgConfidence = avgConf;
        gapVector.subjects[subject].needsWork = avgConf < 3;
    }

    return gapVector;
};

export const saveAssessment = async (userId, assessmentData) => {
    const insertQuery = `
        INSERT INTO assessments (id, user_id, payload, created_at)
        VALUES (gen_random_uuid(), $1, $2, NOW())
        RETURNING id, user_id, payload, created_at
    `;

    const result = await query(insertQuery, [
        userId,
        JSON.stringify(assessmentData)
    ]);

    return result.rows[0];
};

export const getAssessmentById = async (assessmentId, userId) => {
    const selectQuery = `
        SELECT id, user_id, payload, created_at
        FROM assessments
        WHERE id = $1 AND user_id = $2
    `;

    const result = await query(selectQuery, [assessmentId, userId]);
    return result.rows[0] || null;
};

export const getAssessmentsByUser = async (userId, limit = 10) => {
    const selectQuery = `
        SELECT id, payload, created_at
        FROM assessments
        WHERE user_id = $1
        ORDER BY created_at DESC
        LIMIT $2
    `;

    const result = await query(selectQuery, [userId, limit]);
    return result.rows;
};

export const validateAssessmentAnswers = (answers) => {
    if (!answers || typeof answers !== 'object') {
        return { valid: false, message: 'Assessment answers are required' };
    }

    const answerKeys = Object.keys(answers);
    if (answerKeys.length < 6 || answerKeys.length > 7) {
        return { valid: false, message: 'Assessment must contain 6-7 questions' };
    }

    return { valid: true };
};
