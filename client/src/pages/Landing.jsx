import { motion } from 'framer-motion';
import { useAuth } from '../context/AuthContext';
import { ArrowRight, Terminal, Cpu, Database } from 'lucide-react';
import { Navigate } from 'react-router-dom';
import pkg from '../../package.json';
import './Landing.css';

const Landing = () => {
    const { login, user, loading } = useAuth();

    if (user && !loading) {
        return <Navigate to="/dashboard" replace />;
    }

    const glichVariants = {
        hidden: { opacity: 0, x: -10 },
        visible: { opacity: 1, x: 0 }
    };

    return (
        <div className="landing-page">
            <div className="landing-background">
                <div className="grid-overlay"></div>
                <div className="noise-overlay"></div>
            </div>

            <main className="landing-content container">
                <motion.div 
                    initial={{ opacity: 0, y: 50 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8, ease: "easeOut" }}
                    className="hero-section"
                >
                    <div className="status-badge">
                        <span className="status-dot"></span>
                        SYSTEM ONLINE // V {pkg.version}
                    </div>

                    <h1 className="hero-title">
                        <span className="outline-text">EXAM</span>
                        <span className="filled-text">INTEL</span><br />
                        <span className="glitch-text" data-text="AI SUITE">AI SUITE</span>
                    </h1>

                    <p className="hero-subtitle">
                        AI-powered academic recovery using PYQ intelligence. <span className="highlight">Reconstruct your GPA</span> through automated paper analysis and targeted syllabus strategies.
                    </p>

                    <div className="cta-container">
                        <motion.button 
                            whileHover={{ scale: 1.05, backgroundColor: "var(--accent-primary)", color: "#000" }}
                            whileTap={{ scale: 0.95 }}
                            onClick={login}
                            className="primary-cta"
                        >
                            <Terminal size={20} />
                            INITIALIZE PROTOCOL
                            <ArrowRight size={20} />
                        </motion.button>
                    </div>
                </motion.div>
            </main>
        </div>
    );
};

export default Landing;
