import Header from '../components/Header';
import { useState } from 'react';
import { ragAPI } from '../api/client';
import { toast } from 'react-hot-toast';
import { UploadCloud, Link as LinkIcon, FileText, Check, Loader2, Mail } from 'lucide-react';
import { motion } from 'framer-motion';
import './UploadPYQ.css';

const UploadPYQ = () => {
    const [urls, setUrls] = useState('');
    const [loading, setLoading] = useState(false);
    const [jobId, setJobId] = useState(null);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            const urlList = urls.split('\n').filter(u => u.trim());
            const response = await ragAPI.ingest(urlList);
            
            if (response.success) {
                toast.success("Ingestion started");
                setJobId(response.data.jobId);
            }
        } catch (error) {
            console.error(error);
            toast.error("Failed to start ingestion");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="upload-page">
            <Header />
            <main className="container upload-container">
                <motion.div 
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="upload-card"
                >
                    <div className="upload-header">
                        <UploadCloud size={48} className="upload-icon" />
                        <h1>INGEST DATA</h1>
                        <p>Feed the RAG engine with Past Year Question papers (PDF URL).</p>
                    </div>

                    <form onSubmit={handleSubmit} className="upload-form">
                        <div className="input-group">
                            <label>DOCUMENT URLs (ONE PER LINE)</label>
                            <textarea 
                                value={urls}
                                onChange={(e) => setUrls(e.target.value)}
                                placeholder="https://university.edu/papers/2023_CS_101.pdf"
                                rows={5}
                                className="url-input"
                            />
                        </div>

                        <button type="submit" className="ingest-btn" disabled={loading}>
                            {loading ? (
                                <><Loader2 className="spin" /> PROCESSING</>
                            ) : (
                                "INITIATE INGESTION"
                            )}
                        </button>
                    </form>

                    {jobId && (
                        <div className="status-panel">
                            <div className="status-header">
                                <Check size={16} color="var(--accent-primary)" />
                                <span>JOB STATUS: ACTIVE</span>
                            </div>
                            <div className="job-id">ID: {jobId}</div>
                            <div className="status-desc">
                                The engine is currently vectorizing your documents. 
                                This process happens in the background.
                            </div>
                            <div className="email-notification">
                                <Mail size={18} color="var(--accent-primary)" />
                                <span>
                                    You will receive an email notification once the ingestion process completes 
                                    (success/failed). After successful completion, you can start your assessment.
                                </span>
                            </div>
                        </div>
                    )}
                </motion.div>
            </main>
        </div>
    );
};

export default UploadPYQ;
