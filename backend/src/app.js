import express from 'express';
import helmet from 'helmet';
import cors from 'cors';
import config from './config/index.js';
import { rateLimiter } from './middleware/rateLimitMiddleware.js';
import authRouter from './routes/auth.js';
import assessmentRouter from './routes/assessment.js';
import planRouter from './routes/plan.js';
import ragProxyRouter from './routes/ragProxy.js';
import { sendNotFound, sendError } from './utils/response.js';
import log from './utils/logger.js';

const app = express();

app.use(helmet());
app.use(cors({
    origin: config.corsOrigins,
    credentials: config.corsAllowCredentials,
    methods: config.corsAllowMethods,
    allowedHeaders: config.corsAllowHeaders,
}));

app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Apply rate limiting
app.use(rateLimiter);

app.get('/health', (req, res) => {
    res.json({ ok: true });
});

app.use('/api/auth', authRouter);
app.use('/api/assessment', assessmentRouter);
app.use('/api/plan', planRouter);
app.use('/api/rag', ragProxyRouter);

app.use((req, res) => {
    sendNotFound(res, 'Route not found');
});

app.use((err, req, res, next) => {
    log.error('Unhandled error:', err.stack);
    sendError(res, err.message || 'Internal server error', err.status || 500, err);
});

export default app;
