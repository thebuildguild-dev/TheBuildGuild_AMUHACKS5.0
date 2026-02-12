import rateLimit from 'express-rate-limit';
import RedisStore from 'rate-limit-redis';
import { getRedisClient } from '../db/redisClient.js';
import config from '../config/index.js';
import log from '../utils/logger.js';

function createRateLimiter() {
    if (!config.rateLimitEnabled) {
        log.info('Rate limiting is disabled');
        return (req, res, next) => next();
    }

    const options = {
        windowMs: config.rateLimitWindowMs,
        max: config.rateLimitMaxRequests,
        message: {
            success: false,
            message: 'Too many requests, please try again later.',
        },
        standardHeaders: true,
        legacyHeaders: false,
        handler: (req, res) => {
            log.warn(`Rate limit exceeded for IP: ${req.ip}`);
            res.status(429).json({
                success: false,
                message: 'Too many requests, please try again later.',
            });
        },
    };

    // Use Redis store if Redis is enabled
    if (config.redisEnabled) {
        const redisClient = getRedisClient();
        if (redisClient) {
            options.store = new RedisStore({
                sendCommand: (...args) => redisClient.call(...args),
                prefix: 'ratelimit:',
            });
            log.success('Rate limiter using Redis store');
        } else {
            log.warn('Rate limiter using memory store (Redis unavailable)');
        }
    } else {
        log.info('Rate limiter using memory store');
    }

    return rateLimit(options);
}

export const rateLimiter = createRateLimiter();

// Stricter rate limit for auth endpoints
export function createAuthRateLimiter() {
    if (!config.rateLimitEnabled) {
        return (req, res, next) => next();
    }

    const options = {
        windowMs: 15 * 60 * 1000, // 15 minutes
        max: 5, // 5 requests per windowMs
        message: {
            success: false,
            message: 'Too many authentication attempts, please try again later.',
        },
        standardHeaders: true,
        legacyHeaders: false,
    };

    if (config.redisEnabled) {
        const redisClient = getRedisClient();
        if (redisClient) {
            options.store = new RedisStore({
                sendCommand: (...args) => redisClient.call(...args),
                prefix: 'ratelimit:auth:',
            });
        }
    }

    return rateLimit(options);
}

export const authRateLimiter = createAuthRateLimiter();

export default rateLimiter;
