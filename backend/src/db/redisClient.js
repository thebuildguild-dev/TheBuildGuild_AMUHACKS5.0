import Redis from 'ioredis';
import config from '../config/index.js';
import log from '../utils/logger.js';

let redisClient = null;

function createRedisClient() {
    if (!config.redisEnabled) {
        log.info('Redis is disabled');
        return null;
    }

    try {
        const options = {
            host: config.redisHost,
            port: config.redisPort,
            retryStrategy: (times) => {
                const delay = Math.min(times * 50, 2000);
                return delay;
            },
            maxRetriesPerRequest: 3,
        };

        if (config.redisPassword) {
            options.password = config.redisPassword;
        }

        const client = new Redis(options);

        client.on('connect', () => {
            log.success('Redis connected');
        });

        client.on('error', (err) => {
            log.error('Redis connection error:', err.message);
        });

        client.on('ready', () => {
            log.success('Redis ready');
        });

        return client;
    } catch (error) {
        log.error('Failed to create Redis client:', error.message);
        return null;
    }
}

export function getRedisClient() {
    if (!redisClient && config.redisEnabled) {
        redisClient = createRedisClient();
    }
    return redisClient;
}

export async function closeRedisClient() {
    if (redisClient) {
        await redisClient.quit();
        redisClient = null;
        log.info('Redis connection closed');
    }
}

export default {
    getClient: getRedisClient,
    close: closeRedisClient,
};
