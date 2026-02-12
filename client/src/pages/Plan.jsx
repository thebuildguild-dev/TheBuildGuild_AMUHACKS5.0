import Header from '../components/Header';
import { useParams } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { planAPI } from '../api/client';
import { motion } from 'framer-motion';
import { Calendar, CheckSquare, Target, Loader2, Clock, BookOpen, Zap, TrendingUp, AlertTriangle } from 'lucide-react';
import './Plan.css';

const Plan = () => {
    const { planId } = useParams();
    const [plan, setPlan] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchPlan = async () => {
            try {
                const res = await planAPI.getById(planId);
                setPlan(res.data);
            } catch (err) {
                console.error(err);
            } finally {
                setLoading(false);
            }
        };
        fetchPlan();
    }, [planId]);

    if (loading) return (
        <div className="loading-screen">
            <Loader2 className="spin" size={48} />
            <div className="loading-text">DECYPHERING RECOVERY PATH...</div>
        </div>
    );

    if (!plan) return <div className="error-screen">PLAN NOT FOUND // 404</div>;

    const planData = typeof plan.plan === 'string' ? JSON.parse(plan.plan) : plan.plan;
    const { 
        summary = {}, 
        prioritizedTopics = [], 
        weeklySchedule = [], 
        recommendations = [],
        examStrategy = {},
        metadata = {}
    } = planData || {};

    return (
        <div className="plan-page">
            <Header />
            <main className="container plan-container">
                <motion.div 
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="plan-header"
                >
                    <div className="plan-id">PLAN-ID: {planId.slice(0,8).toUpperCase()}</div>
                    <h1 className="plan-title">AI RECOVERY PLAN</h1>
                    <div className="plan-meta">
                        <div className="meta-item">
                            <Target size={18} />
                            <span>{metadata.subject || 'Subject'}</span>
                        </div>
                        <div className="meta-item">
                            <Calendar size={18} />
                            <span>{metadata.daysUntilExam || 0} Days Until Exam</span>
                        </div>
                        <div className="meta-item">
                            <Clock size={18} />
                            <span>{summary.studyHoursPerDay || 0}h/day</span>
                        </div>
                        <div className="meta-item">
                            <TrendingUp size={18} />
                            <span>{summary.confidence || 'Medium'} Confidence</span>
                        </div>
                    </div>
                </motion.div>

                {recommendations && recommendations.length > 0 && (
                    <section className="recommendations-section">
                        <h2><Zap size={20} /> KEY RECOMMENDATIONS</h2>
                        <div className="recommendations-grid">
                            {recommendations.map((rec, i) => (
                                <div key={i} className={`rec-card rec-${rec.type}`}>
                                    {rec.type === 'critical' && <AlertTriangle size={16} />}
                                    {rec.type === 'warning' && <AlertTriangle size={16} />}
                                    {rec.type === 'tip' && <BookOpen size={16} />}
                                    <p>{rec.message}</p>
                                </div>
                            ))}
                        </div>
                    </section>
                )}

                <div className="plan-grid">
                    <section className="topics-section">
                        <h2><Target size={20} /> PRIORITY TOPICS</h2>
                        <div className="topics-list">
                            {prioritizedTopics.slice(0, 10).map((topic, i) => (
                                <motion.div 
                                    key={i} 
                                    initial={{ opacity: 0, x: -20 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    transition={{ delay: i * 0.05 }}
                                    className="topic-card"
                                >
                                    <div className="topic-header">
                                        <div className="topic-index">#{i+1}</div>
                                        <div className="topic-name">{topic.name}</div>
                                        <div className={`difficulty difficulty-${topic.difficulty?.toLowerCase()}`}>
                                            {topic.difficulty || 'Medium'}
                                        </div>
                                    </div>
                                    <div className="topic-stats">
                                        <span className="stat">Priority: {topic.priority?.toFixed(1) || 0}</span>
                                        <span className="stat">PYQ Freq: {topic.pyqFrequency || 0}x</span>
                                        <span className="stat">{topic.hoursNeeded || 0}h needed</span>
                                        <span className="stat">Est. {topic.estimatedMarks || 0} marks</span>
                                    </div>
                                    {topic.strategy && topic.strategy.length > 0 && (
                                        <div className="topic-strategy">
                                            {topic.strategy.slice(0, 2).map((tip, idx) => (
                                                <div key={idx} className="strategy-tip">
                                                    <CheckSquare size={14} /> {tip}
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </motion.div>
                            ))}
                        </div>
                    </section>

                    <section className="schedule-section">
                        <h2><Calendar size={20} /> WEEKLY SCHEDULE</h2>
                        <div className="weekly-timeline">
                            {weeklySchedule.map((week, weekIdx) => (
                                <div key={weekIdx} className="week-block">
                                    <h3 className="week-header">Week {week.week} - {week.focus}</h3>
                                    <div className="daily-schedule">
                                        {week.dailyPlan?.map((day, dayIdx) => (
                                            <div key={dayIdx} className="day-card">
                                                <div className="day-header">
                                                    <span>{day.day}</span>
                                                    <span className="day-hours">{day.hours}h</span>
                                                </div>
                                                <div className="day-content">
                                                    <div className="day-topics">
                                                        {day.topics?.map((topic, idx) => (
                                                            <span key={idx} className="day-topic">{topic}</span>
                                                        ))}
                                                    </div>
                                                    <div className="day-activities">
                                                        {day.activities?.slice(0, 3).map((activity, idx) => (
                                                            <div key={idx} className="activity">
                                                                <CheckSquare size={12} /> {activity}
                                                            </div>
                                                        ))}
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </section>
                </div>

                {examStrategy && Object.keys(examStrategy).length > 0 && (
                    <section className="exam-strategy-section">
                        <h2><Zap size={20} /> EXAM STRATEGY</h2>
                        <div className="strategy-grid">
                            {examStrategy.lastWeek && (
                                <div className="strategy-block">
                                    <h3>Last Week</h3>
                                    <ul>
                                        {examStrategy.lastWeek.map((tip, i) => (
                                            <li key={i}>{tip}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                            {examStrategy.lastDay && (
                                <div className="strategy-block">
                                    <h3>Last Day</h3>
                                    <ul>
                                        {examStrategy.lastDay.map((tip, i) => (
                                            <li key={i}>{tip}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                            {examStrategy.examDay && (
                                <div className="strategy-block">
                                    <h3>Exam Day</h3>
                                    <ul>
                                        {examStrategy.examDay.map((tip, i) => (
                                            <li key={i}>{tip}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                        </div>
                    </section>
                )}
            </main>
        </div>
    );
};

export default Plan;
