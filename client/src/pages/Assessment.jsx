import Header from '../components/Header';
import { useState } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { assessmentAPI } from '../api/client';
import { toast } from 'react-hot-toast'; 
import { BrainCircuit, CheckCircle, AlertCircle } from 'lucide-react';
import './Assessment.css';

const Assessment = () => {
    const navigate = useNavigate();
    const [loading, setLoading] = useState(false);
    
    const [formData, setFormData] = useState({
        examDate: '',
        subject: '',
        topics: '',
        stressLevel: 5,
        syllabusCoverage: 50,
        additionalNotes: ''
    });

    const handleInputChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: value
        }));
    };

    const submitAssessment = async (e) => {
        e.preventDefault();
        
        // Validation
        if (!formData.examDate || !formData.subject) {
            toast.error("Please fill in exam date and subject");
            return;
        }

        setLoading(true);
        try {
            const payload = {
                examDate: formData.examDate,
                subject: formData.subject,
                topics: formData.topics.split(',').map(t => t.trim()).filter(Boolean),
                stressLevel: parseInt(formData.stressLevel),
                syllabusCoverage: parseInt(formData.syllabusCoverage),
                additionalNotes: formData.additionalNotes
            };
            
            const response = await assessmentAPI.submit(payload);
            toast.success("Assessment submitted! Generating your recovery plan...");
            
            if (response.data && response.data.plan) {
                navigate(`/plan/${response.data.plan.id}`);
            } else {
                navigate('/dashboard');
            }

        } catch (error) {
            console.error(error);
            toast.error("Failed to submit assessment");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="assessment-page">
            <Header />
            <div className="container assessment-container">
                <motion.div 
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="assessment-form-card"
                >
                    <div className="form-header">
                        <BrainCircuit size={40} className="header-icon" />
                        <h1>Academic Assessment</h1>
                        <p>Help us understand your current situation to generate a personalized recovery plan</p>
                    </div>

                    <form onSubmit={submitAssessment} className="assessment-form">
                        <div className="form-group">
                            <label htmlFor="examDate">
                                <AlertCircle size={18} />
                                Exam Date
                            </label>
                            <input 
                                type="date"
                                id="examDate"
                                name="examDate"
                                value={formData.examDate}
                                onChange={handleInputChange}
                                required
                                min={new Date().toISOString().split('T')[0]}
                            />
                        </div>

                        <div className="form-group">
                            <label htmlFor="subject">
                                <CheckCircle size={18} />
                                Subject
                            </label>
                            <input 
                                type="text"
                                id="subject"
                                name="subject"
                                placeholder="e.g., Data Structures, DBMS, Operating Systems"
                                value={formData.subject}
                                onChange={handleInputChange}
                                required
                            />
                        </div>

                        <div className="form-group">
                            <label htmlFor="topics">
                                Topics to Focus (comma-separated)
                            </label>
                            <textarea 
                                id="topics"
                                name="topics"
                                placeholder="e.g., Trees, Graphs, Sorting Algorithms"
                                value={formData.topics}
                                onChange={handleInputChange}
                                rows="3"
                            />
                        </div>

                        <div className="form-group">
                            <label htmlFor="stressLevel">
                                Stress Level: {formData.stressLevel}/10
                            </label>
                            <input 
                                type="range"
                                id="stressLevel"
                                name="stressLevel"
                                min="1"
                                max="10"
                                value={formData.stressLevel}
                                onChange={handleInputChange}
                            />
                            <div className="range-labels">
                                <span>Calm</span>
                                <span>Moderate</span>
                                <span>High Stress</span>
                            </div>
                        </div>

                        <div className="form-group">
                            <label htmlFor="syllabusCoverage">
                                Syllabus Coverage: {formData.syllabusCoverage}%
                            </label>
                            <input 
                                type="range"
                                id="syllabusCoverage"
                                name="syllabusCoverage"
                                min="0"
                                max="100"
                                step="5"
                                value={formData.syllabusCoverage}
                                onChange={handleInputChange}
                            />
                            <div className="range-labels">
                                <span>0%</span>
                                <span>50%</span>
                                <span>100%</span>
                            </div>
                        </div>

                        <div className="form-group">
                            <label htmlFor="additionalNotes">
                                Additional Notes (Optional)
                            </label>
                            <textarea 
                                id="additionalNotes"
                                name="additionalNotes"
                                placeholder="Any specific concerns or topics you're struggling with..."
                                value={formData.additionalNotes}
                                onChange={handleInputChange}
                                rows="4"
                            />
                        </div>

                        <button 
                            type="submit" 
                            className="submit-btn"
                            disabled={loading}
                        >
                            {loading ? 'GENERATING PLAN...' : 'GENERATE RECOVERY PLAN'}
                        </button>
                    </form>
                </motion.div>
            </div>
        </div>
    );
};

export default Assessment;
