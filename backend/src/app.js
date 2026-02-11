import express from 'express';
import helmet from 'helmet';
import cors from 'cors';
import authRouter from './routes/auth.js';
import assessmentRouter from './routes/assessment.js';
import planRouter from './routes/plan.js';
import ragProxyRouter from './routes/ragProxy.js';

const app = express();

// Security middleware
app.use(helmet());
app.use(cors());

// Body parser
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Health check
app.get('/health', (req, res) => {
    res.json({ ok: true });
});

// API routes
app.use('/api/auth', authRouter);
app.use('/api/assessment', assessmentRouter);
app.use('/api/plan', planRouter);
app.use('/api/rag', ragProxyRouter);

// 404 handler
app.use((req, res) => {
    res.status(404).json({ error: 'Route not found' });
});

// Error handler
app.use((err, req, res, next) => {
    console.error(err.stack);
    res.status(err.status || 500).json({
        error: err.message || 'Internal server error'
    });
});

export default app;
