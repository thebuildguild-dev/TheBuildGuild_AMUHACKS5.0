import dotenv from 'dotenv';
import app from './app.js';
import log from './utils/logger.js';

dotenv.config();

const PORT = process.env.PORT || 8000;

const server = app.listen(PORT, () => {
    log.success(`ExamIntel Backend running on port ${PORT}`);
    log.info(`Environment: ${process.env.NODE_ENV || 'development'}`);
});

process.on('unhandledRejection', (err) => {
    log.error('UNHANDLED REJECTION! Shutting down...');
    log.error(err.name, err.message);
    server.close(() => {
        process.exit(1);
    });
});

process.on('uncaughtException', (err) => {
    log.error('UNCAUGHT EXCEPTION! Shutting down...');
    log.error(err.name, err.message);
    process.exit(1);
});

process.on('SIGTERM', () => {
    log.info('SIGTERM received. Shutting down gracefully...');
    server.close(() => {
        log.info('Process terminated');
    });
});
