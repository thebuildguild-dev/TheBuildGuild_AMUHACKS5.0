import dotenv from 'dotenv';
import app from './app.js';
import config from './config/index.js';
import log from './utils/logger.js';
import { getRedisClient, closeRedisClient } from './db/redisClient.js';

dotenv.config();

// Initialize Redis connection
getRedisClient();

const server = app.listen(config.port, () => {
    log.success(`ExamIntel Backend running on port ${config.port}`);
    log.info(`Environment: ${config.nodeEnv}`);
});

process.on('unhandledRejection', async (err) => {
    log.error('UNHANDLED REJECTION! Shutting down...');
    log.error(err.name, err.message);
    await closeRedisClient();
    server.close(() => {
        process.exit(1);
    });
});

process.on('uncaughtException', async (err) => {
    log.error('UNCAUGHT EXCEPTION! Shutting down...');
    log.error(err.name, err.message);
    await closeRedisClient();
    process.exit(1);
});

process.on('SIGTERM', async () => {
    log.info('SIGTERM received. Shutting down gracefully...');
    await closeRedisClient();
    server.close(() => {
        log.info('Process terminated');
    });
});
