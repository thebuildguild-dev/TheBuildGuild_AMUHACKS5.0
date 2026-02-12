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
