import { query } from '../db/pgClient.js';
import { queryPYQs } from './ragClient.js';

/**
 * Calculate priority score for a topic
 * Priority = (pyq_freq * avg_marks * understanding_gap * stress_factor) / (current_coverage + 0.1)
 * 
 * @param {number} pyqFreq - Frequency of topic in past year questions
 * @param {number} avgMarks - Average marks allocated to this topic
 * @param {number} understandingGap - Gap score (0-5, higher = more gap)
 * @param {number} stressFactor - User stress level or urgency (1-5)
 * @param {number} currentCoverage - Current coverage level (0-1)
 * @returns {number} Priority score
 */
export const calculatePriority = (
    pyqFreq,
    avgMarks,
    understandingGap,
    stressFactor = 3,
    currentCoverage = 0
) => {
    // Avoid division by zero
    const denominator = Math.max(currentCoverage + 0.1, 0.1);

    return (pyqFreq * avgMarks * understandingGap * stressFactor) / denominator;
};

/**
 * Analyze RAG results to extract topic information
 * @param {Array} ragResults - Results from RAG query
 * @returns {Object} Topic analysis with frequencies and marks
 */
const analyzeTopics = (ragResults) => {
    const topicMap = new Map();

    for (const result of ragResults) {
        const { metadata, score } = result;
        const topic = metadata?.topic || 'Unknown';
        const marks = metadata?.marks || 5; // Default 5 marks if not specified

        if (!topicMap.has(topic)) {
            topicMap.set(topic, {
                name: topic,
                frequency: 0,
                totalMarks: 0,
                avgMarks: 0,
                examples: [],
                relevanceScore: 0,
            });
        }

        const topicData = topicMap.get(topic);
        topicData.frequency += 1;
        topicData.totalMarks += marks;
        topicData.relevanceScore += score;
        topicData.examples.push({
            text: result.text?.substring(0, 200) || '',
            year: metadata?.year,
            marks,
        });
    }

    // Calculate averages
    for (const [topic, data] of topicMap) {
        data.avgMarks = data.frequency > 0 ? data.totalMarks / data.frequency : 5;
        data.relevanceScore = data.frequency > 0 ? data.relevanceScore / data.frequency : 0;
    }

    return topicMap;
};

/**
 * Create a greedy study schedule based on priority-sorted topics
 * @param {Array} prioritizedTopics - Topics sorted by priority
 * @param {number} availableHours - Total hours available for study
 * @param {number} daysAvailable - Number of days until exam
 * @returns {Array} Study schedule with daily blocks
 */
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

/**
 * Generate a personalized recovery plan based on assessment
 * @param {string} userId - User ID
 * @param {Object} assessment - Assessment data with answers and gap vector
 * @returns {Promise<Object>} Generated recovery plan
 */
export const generatePlan = async (userId, assessment) => {
    try {
        const { assessmentId, answers, gapVector } = assessment;

        console.log(`Generating plan for user ${userId}, assessment ${assessmentId}`);

        // Extract subjects from gap vector
        const subjects = Object.keys(gapVector.subjects || {});

        if (subjects.length === 0) {
            throw new Error('No subjects found in assessment');
        }

        // Query RAG for each subject
        const ragPromises = subjects.map(async (subject) => {
            const subjectData = gapVector.subjects[subject];
            const topics = Object.keys(subjectData.topics || {});

            // Create query from weak topics
            const weakTopics = topics.filter(
                topic => subjectData.topics[topic].confidence < 3
            );

            const queryText = weakTopics.length > 0
                ? `Questions about ${weakTopics.join(', ')}`
                : `Common exam questions for ${subject}`;

            const ragResult = await queryPYQs(subject, queryText, 15);

            return {
                subject,
                ragResult,
                subjectData,
            };
        });

        const ragResults = await Promise.all(ragPromises);

        // Build prioritized topic list
        const allTopics = [];

        for (const { subject, ragResult, subjectData } of ragResults) {
            const topicAnalysis = analyzeTopics(ragResult.results);

            for (const [topicName, topicData] of topicAnalysis) {
                // Get understanding gap from assessment
                const topicGap = subjectData.topics[topicName];
                const understandingGap = topicGap?.gapScore || 3.0;
                const confidence = topicGap?.confidence || 2.5;

                // Calculate stress factor based on overall confidence
                const stressFactor = confidence < 2 ? 5 : confidence < 3 ? 4 : 3;

                // Calculate priority score
                const priority = calculatePriority(
                    topicData.frequency,
                    topicData.avgMarks,
                    understandingGap,
                    stressFactor,
                    0 // No current coverage at the start
                );

                // Estimate hours needed (1 hour per 5 marks, scaled by gap)
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
                    examples: topicData.examples.slice(0, 3), // Top 3 examples
                    strategy: generateStrategyTips(topicData, understandingGap),
                });
            }
        }

        // Sort by priority (descending)
        allTopics.sort((a, b) => b.priority - a.priority);

        // Take top N topics for the plan
        const topN = 15;
        const prioritizedTopics = allTopics.slice(0, topN);

        // Calculate total estimated hours
        const totalHours = prioritizedTopics.reduce(
            (sum, topic) => sum + topic.estimatedHours,
            0
        );

        // Generate schedule (assume 2 weeks, adjust as needed)
        const schedule = createSchedule(prioritizedTopics, totalHours, 14);

        // Build final plan
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
        };

        console.log(`Plan generated: ${prioritizedTopics.length} topics, ${totalHours} hours`);

        return plan;
    } catch (error) {
        console.error('Plan generation error:', error);
        throw new Error(`Failed to generate recovery plan: ${error.message}`);
    }
};

/**
 * Generate strategy tips for a topic
 * @param {Object} topicData - Topic analysis data
 * @param {number} understandingGap - Understanding gap score
 * @returns {Array} Strategy tips
 */
const generateStrategyTips = (topicData, understandingGap) => {
    const tips = [];

    if (topicData.frequency > 5) {
        tips.push('High frequency topic - appears in most exams');
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

/**
 * Generate overall recommendations
 * @param {Object} gapVector - Skill gap vector
 * @param {Array} topics - Prioritized topics
 * @returns {Array} Recommendations
 */
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

/**
 * Save recovery plan to database
 * @param {string} userId - User ID
 * @param {string} assessmentId - Assessment ID
 * @param {Object} plan - Recovery plan object
 * @returns {Promise<Object>} Saved plan record
 */
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
        console.error('Save plan error:', error);
        throw new Error(`Failed to save recovery plan: ${error.message}`);
    }
};

/**
 * Format plan data for frontend consumption
 * @param {Object} planData - Raw plan data from database
 * @returns {Object} Formatted plan
 */
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

export default {
    generatePlan,
    savePlan,
    formatPlan,
    calculatePriority,
};
