import { query } from '../db/pgClient.js';
import { performQuery } from './ragService.js';
import log from '../utils/logger.js';
import { GoogleGenerativeAI } from '@google/generative-ai';
import config from '../config/index.js';

const genAI = config.geminiApiKey ? new GoogleGenerativeAI(config.geminiApiKey) : null;

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

export const generatePlan = async (userId, assessmentData) => {
    try {
        const {
            examDate,
            subject,
            topics,
            stressLevel,
            syllabusCoverage,
            additionalNotes
        } = assessmentData;

        log.info(`Generating AI plan for user ${userId}, subject: ${subject}`);

        if (!genAI) {
            throw new Error('Gemini AI not configured - missing GEMINI_API_KEY');
        }

        const daysUntilExam = Math.max(1, Math.ceil((new Date(examDate) - new Date()) / (1000 * 60 * 60 * 24)));
        const topicsList = Array.isArray(topics) ? topics : [];

        const queryText = topicsList.length > 0
            ? `${subject}: ${topicsList.join(', ')}`
            : subject;

        log.info(`Querying RAG for subject: ${subject}, topics: ${topicsList.join(', ')}`);
        const ragResult = await performQuery(userId, subject, queryText, 20);

        const pyqAnalysis = analyzeRAGResults(ragResult.results || []);

        const prompt = `You are an expert academic recovery planner. Generate a comprehensive study plan based on the following:

**Student Situation:**
- Exam Date: ${examDate} (${daysUntilExam} days remaining)
- Subject: ${subject}
- Focus Topics: ${topicsList.length > 0 ? topicsList.join(', ') : 'General coverage'}
- Current Syllabus Coverage: ${syllabusCoverage}%
- Stress Level: ${stressLevel}/10
- Additional Notes: ${additionalNotes || 'None'}

**Past Year Question (PYQ) Analysis:**
${pyqAnalysis.summary}

**Priority Calculation Formula:**
Priority = (PYQ_Frequency × Average_Marks × Understanding_Gap × Stress_Factor) / (Current_Coverage + 0.1)

Where:
- PYQ_Frequency: How often topic appears in past papers (from analysis above)
- Average_Marks: Expected marks per topic (3-10 range)
- Understanding_Gap: Inversely related to syllabus coverage (10 - syllabusCoverage/10)
- Stress_Factor: ${stressLevel}
- Current_Coverage: ${syllabusCoverage / 100}

**Generate a JSON recovery plan with:**
{
  "summary": {
    "totalDays": ${daysUntilExam},
    "studyHoursPerDay": <calculated based on stress and coverage>,
    "totalTopics": <number>,
    "confidence": "<Low/Medium/High based on days and coverage>"
  },
  "prioritizedTopics": [
    {
      "name": "<topic name>",
      "priority": <calculated using formula above>,
      "pyqFrequency": <from analysis>,
      "estimatedMarks": <3-10>,
      "hoursNeeded": <calculated>,
      "difficulty": "<Easy/Medium/Hard>",
      "strategy": ["<specific tip 1>", "<specific tip 2>"]
    }
  ],
  "weeklySchedule": [
    {
      "week": 1,
      "focus": "<main focus area>",
      "dailyPlan": [
        {
          "day": "Day 1",
          "topics": ["<topic 1>", "<topic 2>"],
          "hours": <number>,
          "activities": ["<activity 1>", "<activity 2>", "<activity 3>"]
        }
      ]
    }
  ],
  "recommendations": [
    {
      "type": "critical",
      "message": "<actionable recommendation>"
    }
  ],
  "examStrategy": {
    "lastWeek": ["<tip 1>", "<tip 2>"],
    "lastDay": ["<tip 1>", "<tip 2>"],
    "examDay": ["<tip 1>", "<tip 2>"]
  }
}

**CRITICAL REQUIREMENTS:**
1. MUST include weeklySchedule array with at least one week
2. Each week MUST have dailyPlan array with specific daily breakdown
3. Distribute ${daysUntilExam} days across appropriate number of weeks
4. Each day in dailyPlan MUST specify topics, hours, and activities
5. Use the PYQ analysis to prioritize topics that appear frequently
6. Consider the stress level (${stressLevel}/10) and days available
7. Make the plan realistic and actionable`;

        const model = genAI.getGenerativeModel({ model: config.geminiModel });
        const result = await model.generateContent(prompt);
        const responseText = result.response.text();

        log.info(`Gemini response received, length: ${responseText.length} chars`);

        const jsonMatch = responseText.match(/\{[\s\S]*\}/);
        if (!jsonMatch) {
            log.error('Gemini response did not contain valid JSON');
            throw new Error('Gemini response did not contain valid JSON');
        }

        const aiPlan = JSON.parse(jsonMatch[0]);

        log.info(`AI plan parsed: ${aiPlan.prioritizedTopics?.length || 0} topics, ${aiPlan.weeklySchedule?.length || 0} weeks`);

        const enhancedPlan = {
            ...aiPlan,
            metadata: {
                generatedAt: new Date().toISOString(),
                examDate,
                subject,
                daysUntilExam,
                stressLevel,
                syllabusCoverage,
                pyqDataUsed: pyqAnalysis.totalDocuments,
                generatedBy: 'Gemini AI'
            },
            pyqInsights: pyqAnalysis.topics,
            ragAnalysis: ragResult.analysis || {}
        };

        log.success(`AI plan generated: ${enhancedPlan.prioritizedTopics?.length || 0} topics`);

        return enhancedPlan;
    } catch (error) {
        log.error('AI Plan generation error:', error.message);
        throw new Error(`Failed to generate recovery plan: ${error.message}`);
    }
};

const analyzeRAGResults = (ragResults) => {
    if (!ragResults || ragResults.length === 0) {
        return {
            summary: 'No PYQ data available for this subject.',
            totalDocuments: 0,
            topics: []
        };
    }

    const topicMap = new Map();

    for (const result of ragResults) {
        const { metadata, score } = result;
        const papers = metadata?.papers || [];

        for (const paper of papers) {
            const topics = paper.topics || [paper.subject || 'General'];
            const year = paper.year;
            const difficulty = paper.difficulty || 'medium';

            for (const topic of topics) {
                if (!topicMap.has(topic)) {
                    topicMap.set(topic, {
                        name: topic,
                        frequency: 0,
                        years: new Set(),
                        avgScore: 0,
                        totalScore: 0,
                        difficulty
                    });
                }

                const topicData = topicMap.get(topic);
                topicData.frequency += 1;
                topicData.totalScore += score;
                if (year) topicData.years.add(year);
            }
        }
    }

    const topics = Array.from(topicMap.values()).map(t => ({
        name: t.name,
        frequency: t.frequency,
        yearCount: t.years.size,
        avgRelevance: (t.totalScore / t.frequency).toFixed(2),
        difficulty: t.difficulty
    })).sort((a, b) => b.frequency - a.frequency);

    const summaryLines = [
        `Found ${ragResults.length} relevant PYQ documents.`,
        `Identified ${topics.length} distinct topics from past papers.`,
        topics.length > 0 ? `Top topics by frequency: ${topics.slice(0, 5).map(t => `${t.name} (${t.frequency}x)`).join(', ')}` : ''
    ].filter(Boolean);

    return {
        summary: summaryLines.join('\n'),
        totalDocuments: ragResults.length,
        topics: topics.slice(0, 15)
    };
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
        plan: planData.plan,
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
            examDate: row.assessment_payload.examDate,
            subject: row.assessment_payload.subject,
            topics: row.assessment_payload.topics || [],
            stressLevel: row.assessment_payload.stressLevel,
            syllabusCoverage: row.assessment_payload.syllabusCoverage
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
