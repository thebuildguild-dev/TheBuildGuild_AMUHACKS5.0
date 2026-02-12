import React from 'react';
import { motion } from 'framer-motion';
import './Footer.css';

const Footer = () => {
    return (
        <motion.footer 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5, duration: 1 }}
            className="stats-ticker"
        >
            <div className="ticker-static-left">
                <span className="live-dot"></span>
                SYSTEM ACTIVE
            </div>
            <div className="ticker-wrapper-fade">
                <div className="ticker-content">
                    <span className="ticker-label">ARCHITECTS: <span style={{ color: "var(--accent-primary)" }}>THE BUILD GUILD</span></span>
                    <span className="ticker-divider">//</span>
                    <span className="ticker-item">SANDIPAN SINGH</span>
                    <span className="ticker-dot">::</span>
                    <span className="ticker-item">ZULEKHA AALMI</span>
                    <span className="ticker-dot">::</span>
                    <span className="ticker-item">ASHUTOSH JHA</span>
                    <span className="ticker-dot">::</span>
                    <span className="ticker-item">KARMAN SINGH CHANDHOK</span>
                    
                    <span className="ticker-divider">//</span>
                    <span className="ticker-label">ARCHITECTS: <span style={{ color: "var(--accent-primary)" }}>THE BUILD GUILD</span></span>
                    <span className="ticker-divider">//</span>
                    <span className="ticker-item">SANDIPAN SINGH</span>
                    <span className="ticker-dot">::</span>
                    <span className="ticker-item">ZULEKHA AALMI</span>
                    <span className="ticker-dot">::</span>
                    <span className="ticker-item">ASHUTOSH JHA</span>
                    <span className="ticker-dot">::</span>
                    <span className="ticker-item">KARMAN SINGH CHANDHOK</span>
                </div>
            </div>
            <div className="ticker-static-right">
                © 2026 TBG
            </div>
        </motion.footer>
    );
};

export default Footer;
