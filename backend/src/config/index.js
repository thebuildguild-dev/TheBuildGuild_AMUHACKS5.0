import dotenv from 'dotenv';

dotenv.config();

const config = {
    port: process.env.PORT || 8000,
    nodeEnv: process.env.NODE_ENV || 'development',

    // Database
    databaseUrl: process.env.DATABASE_URL || 'postgresql://postgres:postgres@localhost:5432/amu_recovery',

    // Firebase
    firebaseProjectId: process.env.FIREBASE_PROJECT_ID,
    firebaseCredentialsJson: process.env.FIREBASE_CREDENTIALS_JSON,

    // RAG Service
    ragUrl: process.env.RAG_URL || 'http://rag:8000',

    // Qdrant
    qdrantDumpPath: process.env.QDRANT_DUMP_PATH,
};

// Validate required config
const requiredVars = ['firebaseProjectId'];
for (const varName of requiredVars) {
    if (!config[varName]) {
        console.warn(`Warning: ${varName} is not set in environment variables`);
    }
}

export default config;
