import { query } from '../db/pgClient.js';
import { performQuery } from './ragService.js';
import log from '../utils/logger.js';

export const calculatePriority = (
    pyqFreq,
    avgMarks,
    understandingGap,
    stressFactor = 3,
    currentCoverage = 0
) => {
    const denominator = Math.max(currentCoverage + 0.1, 0.1);
    return (pyqFreq * avgMarks * understandingGap * stressFactor) / denominator;
};

const analyzeTopics = (ragResults) => {
    const topicMap = new Map();

    for (const result of ragResults) {
        const { metadata, score } = result;
        const papers = metadata?.papers || [];

        if (!papers || papers.length === 0) {
            continue;
        }

        for (const paper of papers) {
            const topics = paper.topics || [];
            const subject = paper.subject || 'Unknown';
            const year = paper.year;
            const difficulty = paper.difficulty || 'medium';

            const estimatedMarks = difficulty === 'hard' ? 8 : difficulty === 'easy' ? 3 : 5;

            if (topics.length === 0) {
                topics.push(subject);
            }

            for (const topic of topics) {
                if (!topicMap.has(topic)) {
                    topicMap.set(topic, {
                        name: topic,
                        frequency: 0,
                        totalMarks: 0,
                        avgMarks: 0,
                        examples: [],
                        relevanceScore: 0,
                        years: new Set(),
                    });
                }

                const topicData = topicMap.get(topic);
                topicData.frequency += 1;
                topicData.totalMarks += estimatedMarks;
                topicData.relevanceScore += score;
                topicData.examples.push({
                    text: result.text?.substring(0, 200) || '',
                    year: year,
                    subject: subject,
                    marks: estimatedMarks,
                });

                if (year) {
                    topicData.years.add(year);
                }
            }
        }
    }

    for (const [topic, data] of topicMap) {
        data.avgMarks = data.frequency > 0 ? data.totalMarks / data.frequency : 5;
        data.relevanceScore = data.frequency > 0 ? data.relevanceScore / data.frequency : 0;
        data.yearCount = data.years.size;
        delete data.years;
    }

    return topicMap;
};

const createSchedule = (prioritizedTopics, availableHours = 40, daysAvailable = 14) => {
    const schedule = [];
    const hoursPerDay = availableHours / daysAvailable;
    let remainingHours = availableHours;

    for (let day = 1; day <= daysAvailable && remainingHours > 0; day++) {
        const dailyBlocks = [];
        let dailyHours = 0;

        for (const topic of prioritizedTopics) {
            if (dailyHours >= hoursPerDay) break;
            if (topic.scheduledHours >= topic.estimatedHours) continue;

            // Allocate time to this topic
            const hoursToAllocate = Math.min(
                topic.estimatedHours - topic.scheduledHours,
                hoursPerDay - dailyHours,
                2 // Max 2 hours per topic per day
            );

            if (hoursToAllocate > 0) {
                dailyBlocks.push({
                    topic: topic.name,
                    subject: topic.subject,
                    hours: hoursToAllocate,
                    priority: topic.priority,
                    activities: [
                        'Review PYQ examples',
                        'Practice problems',
                        'Revise weak concepts',
                    ],
                });

                topic.scheduledHours += hoursToAllocate;
                dailyHours += hoursToAllocate;
                remainingHours -= hoursToAllocate;
            }
        }

        schedule.push({
            day,
            date: new Date(Date.now() + day * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
            totalHours: dailyHours,
            blocks: dailyBlocks,
        });
    }

    return schedule;
};

export const generatePlan = async (userId, assessment) => {
    try {
        const { assessmentId, answers, gapVector } = assessment;

        log.info(`Generating plan for user ${userId}, assessment ${assessmentId}`);

        const subjects = Object.keys(gapVector.subjects || {});

        if (subjects.length === 0) {
            throw new Error('No subjects found in assessment');
        }

        const ragPromises = subjects.map(async (subject) => {
            const subjectData = gapVector.subjects[subject];
            const topics = Object.keys(subjectData.topics || {});

            const weakTopics = topics.filter(
                topic => subjectData.topics[topic].confidence < 3
            );

            const queryText = weakTopics.length > 0
                ? `Questions about ${weakTopics.join(', ')}`
                : `Common exam questions for ${subject}`;

            const ragResult = await performQuery(userId, subject, queryText, 15);

            return {
                subject,
                ragResult,
                subjectData,
            };
        });

        const ragResults = await Promise.all(ragPromises);

        const allTopics = [];
        const subjectAnalysis = {};

        for (const { subject, ragResult, subjectData } of ragResults) {
            const hasResults = ragResult.results && ragResult.results.length > 0;

            if (hasResults) {
                const topicAnalysis = analyzeTopics(ragResult.results);

                for (const [topicName, topicData] of topicAnalysis) {
                    const topicGap = subjectData.topics[topicName];
                    const understandingGap = topicGap?.gapScore || 3.0;
                    const confidence = topicGap?.confidence || 2.5;

                    const stressFactor = confidence < 2 ? 5 : confidence < 3 ? 4 : 3;

                    const priority = calculatePriority(
                        topicData.frequency,
                        topicData.avgMarks,
                        understandingGap,
                        stressFactor,
                        0
                    );

                    const estimatedHours = Math.ceil((topicData.avgMarks / 5) * understandingGap);

                    allTopics.push({
                        subject,
                        name: topicName,
                        priority,
                        frequency: topicData.frequency,
                        avgMarks: topicData.avgMarks,
                        understandingGap,
                        confidence,
                        stressFactor,
                        estimatedHours,
                        scheduledHours: 0,
                        examples: topicData.examples.slice(0, 3),
                        strategy: generateStrategyTips(topicData, understandingGap),
                        yearCount: topicData.yearCount || 0,
                    });
                }

                subjectAnalysis[subject] = ragResult.analysis || {};
            } else {
                log.warn(`No RAG results for subject ${subject}`);

                const assessmentTopics = Object.keys(subjectData.topics || {});
                for (const topicName of assessmentTopics) {
                    const topicGap = subjectData.topics[topicName];
                    const understandingGap = topicGap?.gapScore || 3.0;
                    const confidence = topicGap?.confidence || 2.5;

                    allTopics.push({
                        subject,
                        name: topicName,
                        priority: understandingGap * 10,
                        frequency: 1,
                        avgMarks: 5,
                        understandingGap,
                        confidence,
                        stressFactor: confidence < 3 ? 4 : 3,
                        estimatedHours: Math.ceil(understandingGap * 2),
                        scheduledHours: 0,
                        examples: [],
                        strategy: ['Focus on fundamentals - no PYQ data available'],
                        yearCount: 0,
                    });
                }
            }
        }

        allTopics.sort((a, b) => b.priority - a.priority);

        const topN = 15;
        const prioritizedTopics = allTopics.slice(0, topN);
        const totalHours = prioritizedTopics.reduce(
            (sum, topic) => sum + topic.estimatedHours,
            0
        );

        const schedule = createSchedule(prioritizedTopics, totalHours, 14);
        const plan = {
            assessmentId,
            userId,
            generatedAt: new Date().toISOString(),
            summary: {
                totalTopics: prioritizedTopics.length,
                totalHours,
                subjects: subjects.length,
                overallConfidence: gapVector.overallConfidence,
                weakAreas: gapVector.weakAreas?.length || 0,
            },
            topics: prioritizedTopics,
            schedule,
            recommendations: generateRecommendations(gapVector, prioritizedTopics),
            subjectInsights: subjectAnalysis,
        };

        log.success(`Plan generated: ${prioritizedTopics.length} topics, ${totalHours} hours`);

        return plan;
    } catch (error) {
        log.error('Plan generation error:', error.message);
        throw new Error(`Failed to generate recovery plan: ${error.message}`);
    }
};

const generateStrategyTips = (topicData, understandingGap) => {
    const tips = [];

    if (topicData.frequency > 5) {
        tips.push('High frequency topic - appears in most exams');
    }

    if (topicData.yearCount && topicData.yearCount > 3) {
        tips.push(`Consistent topic - appeared in ${topicData.yearCount} different years`);
    }

    if (topicData.avgMarks > 7) {
        tips.push('High-value topic - carries significant marks');
    }

    if (understandingGap > 3.5) {
        tips.push('Focus on fundamentals first before attempting PYQs');
    } else {
        tips.push('Practice PYQs to improve speed and accuracy');
    }

    tips.push('Review marking scheme and common mistakes');

    return tips;
};

const generateRecommendations = (gapVector, topics) => {
    const recommendations = [];

    if (gapVector.overallConfidence < 2.5) {
        recommendations.push({
            type: 'critical',
            message: 'Focus on understanding core concepts before attempting advanced problems',
        });
    }

    const highPriorityCount = topics.filter(t => t.priority > 50).length;
    if (highPriorityCount > 10) {
        recommendations.push({
            type: 'warning',
            message: 'Many high-priority topics identified. Consider extending study time or prioritizing ruthlessly.',
        });
    }

    recommendations.push({
        type: 'tip',
        message: 'Practice PYQs in exam conditions to build time management skills',
    });

    recommendations.push({
        type: 'tip',
        message: 'Review your weak areas daily to reinforce learning',
    });

    return recommendations;
};

export const savePlan = async (userId, assessmentId, plan) => {
    try {
        const insertQuery = `
      INSERT INTO recovery_plans (id, user_id, assessment_id, plan, created_at, updated_at)
      VALUES (gen_random_uuid(), $1, $2, $3, NOW(), NOW())
      RETURNING id, user_id, assessment_id, plan, created_at, updated_at
    `;

        const result = await query(insertQuery, [
            userId,
            assessmentId,
            JSON.stringify(plan),
        ]);

        return result.rows[0];
    } catch (error) {
        log.error('Save plan error:', error.message);
        throw new Error(`Failed to save recovery plan: ${error.message}`);
    }
};

export const formatPlan = (planData) => {
    return {
        id: planData.id,
        userId: planData.user_id,
        assessmentId: planData.assessment_id,
        plan: typeof planData.plan === 'string' ? JSON.parse(planData.plan) : planData.plan,
        createdAt: planData.created_at,
        updatedAt: planData.updated_at,
    };
};

export const getPlanById = async (planId, userId) => {
    const selectQuery = `
        SELECT id, user_id, assessment_id, plan, created_at, updated_at
        FROM recovery_plans
        WHERE id = $1 AND user_id = $2
    `;

    const result = await query(selectQuery, [planId, userId]);
    return result.rows[0] || null;
};

export const checkAssessmentExists = async (assessmentId, userId) => {
    const result = await query(
        'SELECT id FROM assessments WHERE id = $1 AND user_id = $2',
        [assessmentId, userId]
    );
    return result.rows.length > 0;
};

export const getUserPlansList = async (userId, limit = 20) => {
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
        LIMIT $2
    `;

    const result = await query(selectQuery, [userId, limit]);

    return result.rows.map(row => ({
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
};

export const updatePlanById = async (planId, userId, planData) => {
    const updateQuery = `
        UPDATE recovery_plans
        SET plan = $1, updated_at = NOW()
        WHERE id = $2 AND user_id = $3
        RETURNING id, user_id, assessment_id, plan, created_at, updated_at
    `;

    const result = await query(updateQuery, [
        JSON.stringify(planData),
        planId,
        userId,
    ]);

    return result.rows[0] || null;
};

export default {
    generatePlan,
    savePlan,
    formatPlan,
    calculatePriority,
    getPlanById,
    checkAssessmentExists,
    getUserPlansList,
    updatePlanById,
};
