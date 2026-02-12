import dotenv from 'dotenv';

dotenv.config();

const config = {
    port: process.env.PORT || 8000,
    nodeEnv: process.env.NODE_ENV || 'development',

    // Database
    databaseUrl: process.env.DATABASE_URL || 'postgresql://postgres:postgres@localhost:5432/examintel_db',

    // Firebase
    firebaseProjectId: process.env.FIREBASE_PROJECT_ID,
    firebaseCredentialsJson: process.env.FIREBASE_CREDENTIALS_JSON,

    // RAG Service
    ragUrl: process.env.RAG_URL || 'http://rag:8001',

    // Gemini AI
    geminiApiKey: process.env.GEMINI_API_KEY,
    geminiModel: process.env.GEMINI_MODEL || 'gemini-2.0-flash-exp',

    // Redis
    redisEnabled: process.env.REDIS_ENABLED === 'true',
    redisHost: process.env.REDIS_HOST || 'redis',
    redisPort: parseInt(process.env.REDIS_PORT || '6379', 10),
    redisPassword: process.env.REDIS_PASSWORD || '',

    // Rate Limiting
    rateLimitEnabled: process.env.RATE_LIMIT_ENABLED !== 'false',
    rateLimitWindowMs: parseInt(process.env.RATE_LIMIT_WINDOW_MS || '60000', 10), // 1 minute default
    rateLimitMaxRequests: parseInt(process.env.RATE_LIMIT_MAX_REQUESTS || '100', 10), // 100 requests default

    // Email (Resend)
    resendApiKey: process.env.RESEND_API_KEY,
    emailFrom: process.env.EMAIL_FROM || 'noreply@notifications.thebuildguild.dev',

    // CORS
    corsOrigins: process.env.CORS_ORIGINS ? process.env.CORS_ORIGINS.split(',') : ['http://localhost:3000'],
    corsAllowCredentials: process.env.CORS_ALLOW_CREDENTIALS === 'true',
    corsAllowMethods: process.env.CORS_ALLOW_METHODS || '*',
    corsAllowHeaders: process.env.CORS_ALLOW_HEADERS || '*',
};

// Validate required config
const requiredVars = ['firebaseProjectId'];
for (const varName of requiredVars) {
    if (!config[varName]) {
        console.warn(`Warning: ${varName} is not set in environment variables`);
    }
}

export default config;
