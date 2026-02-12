import Header from '../components/Header';
import { useEffect, useState } from 'react';
import { assessmentAPI, planAPI } from '../api/client';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { Calendar, FileText, Target, Clock, TrendingUp, Loader2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import './History.css';

const History = () => {
    const navigate = useNavigate();
    const { user } = useAuth();
    const [assessments, setAssessments] = useState([]);
    const [plans, setPlans] = useState([]);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('plans');

    useEffect(() => {
        if (!user) {
            setLoading(false);
            return;
        }

        const fetchHistory = async () => {
            try {
                const [assessmentsRes, plansRes] = await Promise.all([
                    assessmentAPI.getUserHistory(),
                    planAPI.getUserHistory()
                ]);
                setAssessments(assessmentsRes.data || []);
                setPlans(plansRes.data || []);
            } catch (error) {
                console.error('Failed to fetch history:', error);
            } finally {
                setLoading(false);
            }
        };
        fetchHistory();
    }, [user]);

    if (loading) {
        return (
            <div className="loading-screen">
                <Loader2 className="spin" size={48} />
                <div className="loading-text">LOADING HISTORY...</div>
            </div>
        );
    }

    const formatDate = (dateString) => {
        return new Date(dateString).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    };

    return (
        <div className="history-page">
            <Header />
            <main className="container history-container">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="history-header"
                >
                    <h1>YOUR HISTORY</h1>
                    <p>Track your assessments and recovery plans</p>
                </motion.div>

                <div className="tabs">
                    <button
                        className={`tab ${activeTab === 'plans' ? 'active' : ''}`}
                        onClick={() => setActiveTab('plans')}
                    >
                        <Target size={18} />
                        Recovery Plans ({plans.length})
                    </button>
                    <button
                        className={`tab ${activeTab === 'assessments' ? 'active' : ''}`}
                        onClick={() => setActiveTab('assessments')}
                    >
                        <FileText size={18} />
                        Assessments ({assessments.length})
                    </button>
                </div>

                {activeTab === 'plans' && (
                    <section className="plans-section">
                        {plans.length === 0 ? (
                            <div className="empty-state">
                                <Target size={48} />
                                <h3>No recovery plans yet</h3>
                                <p>Complete an assessment to generate your first plan</p>
                                <button onClick={() => navigate('/assessment')} className="cta-btn">
                                    Start Assessment
                                </button>
                            </div>
                        ) : (
                            <div className="plans-grid">
                                {plans.map((planItem, idx) => {
                                    const planData = typeof planItem.plan === 'string' 
                                        ? JSON.parse(planItem.plan) 
                                        : planItem.plan;
                                    const metadata = planData?.metadata || {};
                                    const summary = planData?.summary || {};

                                    return (
                                        <motion.div
                                            key={planItem.id}
                                            initial={{ opacity: 0, y: 20 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            transition={{ delay: idx * 0.05 }}
                                            className="plan-card"
                                            onClick={() => navigate(`/plan/${planItem.id}`)}
                                        >
                                            <div className="plan-card-header">
                                                <div className="plan-subject">
                                                    {metadata.subject || 'Subject'}
                                                </div>
                                                <div className="plan-date">
                                                    {formatDate(planItem.createdAt || planItem.created_at)}
                                                </div>
                                            </div>
                                            <div className="plan-card-stats">
                                                <div className="stat-item">
                                                    <Calendar size={16} />
                                                    <span>{metadata.daysUntilExam || 0} days</span>
                                                </div>
                                                <div className="stat-item">
                                                    <Target size={16} />
                                                    <span>{summary.totalTopics || 0} topics</span>
                                                </div>
                                                <div className="stat-item">
                                                    <Clock size={16} />
                                                    <span>{summary.studyHoursPerDay || 0}h/day</span>
                                                </div>
                                                <div className="stat-item">
                                                    <TrendingUp size={16} />
                                                    <span>{summary.confidence || 'Medium'}</span>
                                                </div>
                                            </div>
                                            <div className="plan-card-footer">
                                                <span className="view-plan">View Plan →</span>
                                            </div>
                                        </motion.div>
                                    );
                                })}
                            </div>
                        )}
                    </section>
                )}

                {activeTab === 'assessments' && (
                    <section className="assessments-section">
                        {assessments.length === 0 ? (
                            <div className="empty-state">
                                <FileText size={48} />
                                <h3>No assessments yet</h3>
                                <p>Take your first assessment to analyze your academic gaps</p>
                                <button onClick={() => navigate('/assessment')} className="cta-btn">
                                    Start Assessment
                                </button>
                            </div>
                        ) : (
                            <div className="assessments-list">
                                {assessments.map((assessment, idx) => {
                                    const payload = typeof assessment.payload === 'string'
                                        ? JSON.parse(assessment.payload)
                                        : assessment.payload;

                                    return (
                                        <motion.div
                                            key={assessment.id}
                                            initial={{ opacity: 0, x: -20 }}
                                            animate={{ opacity: 1, x: 0 }}
                                            transition={{ delay: idx * 0.05 }}
                                            className="assessment-card"
                                        >
                                            <div className="assessment-header">
                                                <div className="assessment-title">
                                                    <FileText size={20} />
                                                    <h3>{payload.subject || 'Assessment'}</h3>
                                                </div>
                                                <div className="assessment-date">
                                                    {formatDate(assessment.created_at)}
                                                </div>
                                            </div>
                                            <div className="assessment-details">
                                                <div className="detail-row">
                                                    <span className="detail-label">Exam Date:</span>
                                                    <span className="detail-value">
                                                        {payload.examDate ? formatDate(payload.examDate) : 'N/A'}
                                                    </span>
                                                </div>
                                                <div className="detail-row">
                                                    <span className="detail-label">Coverage:</span>
                                                    <span className="detail-value">{payload.syllabusCoverage || 0}%</span>
                                                </div>
                                                <div className="detail-row">
                                                    <span className="detail-label">Stress Level:</span>
                                                    <span className="detail-value">{payload.stressLevel || 5}/10</span>
                                                </div>
                                                {payload.topics && payload.topics.length > 0 && (
                                                    <div className="detail-row">
                                                        <span className="detail-label">Topics:</span>
                                                        <span className="detail-value">
                                                            {payload.topics.join(', ')}
                                                        </span>
                                                    </div>
                                                )}
                                            </div>
                                        </motion.div>
                                    );
                                })}
                            </div>
                        )}
                    </section>
                )}
            </main>
        </div>
    );
};

export default History;
