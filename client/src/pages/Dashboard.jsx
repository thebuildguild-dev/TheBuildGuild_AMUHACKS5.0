import { useState, useEffect } from 'react';
import Header from '../components/Header';
import { useAuth } from '../context/AuthContext';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { BrainCircuit, UploadCloud, History, ArrowUpRight, FileText } from 'lucide-react';
import { assessmentAPI, planAPI, ragAPI } from '../api/client';
import './Dashboard.css';

const Dashboard = () => {
    const { user } = useAuth();
    const [stats, setStats] = useState([
        { label: "Assessments", value: "0", icon: <BrainCircuit size={24} /> },
        { label: "Recovery Plans", value: "0", icon: <FileText size={24} /> },
        { label: "PYQs Processed", value: "0", icon: <UploadCloud size={24} /> },
    ]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchData = async () => {
            if (!user) {
                setLoading(false);
                return;
            }

            try {
                const [assessmentsRes, plansRes, ragStatsRes] = await Promise.all([
                    assessmentAPI.getUserHistory(),
                    planAPI.getUserHistory(),
                    ragAPI.getStats()
                ]);

                // Update stats based on real data
                const assessmentCount = assessmentsRes.data?.length || 0;
                const planCount = plansRes.data?.length || 0;
                const pyqCount = ragStatsRes.data?.unique_documents || 0;

                setStats([
                    { label: "Assessments", value: assessmentCount.toString(), icon: <BrainCircuit size={24} /> },
                    { label: "Recovery Plans", value: planCount.toString(), icon: <FileText size={24} /> },
                    { label: "PYQs Processed", value: pyqCount.toString(), icon: <UploadCloud size={24} /> },
                ]);
            } catch (error) {
                console.error("Error fetching dashboard data:", error);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, [user]);

    return (
        <div className="dashboard-page">
            <Header />
            <main className="dashboard-content container">
                <motion.div 
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="welcome-section"
                >
                    <h1 className="welcome-title">
                        WELCOME BACK, <span className="highlight-text">{user?.displayName?.split(' ')[0] || 'SCHOLAR'}</span>
                    </h1>
                    <p className="welcome-subtitle">
                        Academic recovery systems operational. 
                        Select a protocol to proceed.
                    </p>
                </motion.div>

                <div className="dashboard-grid">
                    <section className="stats-col">
                        {stats.map((stat, i) => (
                            <motion.div 
                                key={i}
                                initial={{ opacity: 0, x: -20 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: i * 0.1 }}
                                className="stat-card box-border"
                            >
                                <div className="stat-icon">{stat.icon}</div>
                                <div className="stat-value">{loading ? "..." : stat.value}</div>
                                <div className="stat-label">{stat.label}</div>
                            </motion.div>
                        ))}
                    </section>

                    <section className="actions-col">
                        <Link to="/assessment" className="action-card large accent-border">
                            <div className="action-header">
                                <BrainCircuit className="action-icon" />
                                <h2>NEW ASSESSMENT</h2>
                            </div>
                            <p>Generate a new syllabus recovery plan based on gap analysis.</p>
                            <ArrowUpRight className="arrow-icon" />
                        </Link>
                        
                        <div className="sub-actions">
                            <Link to="/upload-pyq" className="action-card small">
                                <div className="action-header">
                                    <UploadCloud className="action-icon" />
                                    <h3>UPLOAD PYQ</h3>
                                </div>
                                <ArrowUpRight className="arrow-icon" />
                            </Link>

                            <Link to="/history" className="action-card small">
                                <div className="action-header">
                                    <History className="action-icon" />
                                    <h3>HISTORY</h3>
                                </div>
                                <ArrowUpRight className="arrow-icon" />
                            </Link>
                        </div>
                    </section>
                </div>
            </main>
        </div>
    );
};

export default Dashboard;
