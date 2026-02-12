import pg from 'pg';
import config from '../config/index.js';
import log from '../utils/logger.js';

const { Pool } = pg;

const pool = new Pool({
    connectionString: config.databaseUrl,
    max: 20,
    idleTimeoutMillis: 30000,
    connectionTimeoutMillis: 2000,
});

pool.on('connect', () => {
    log.success('Connected to PostgreSQL database');
});

pool.on('error', (err) => {
    log.error('Unexpected error on idle PostgreSQL client', err);
    process.exit(-1);
});

export const query = async (text, params) => {
    const start = Date.now();
    try {
        const res = await pool.query(text, params);
        const duration = Date.now() - start;
        log.debug('Executed query', { text: text.substring(0, 100), duration, rows: res.rowCount });
        return res;
    } catch (error) {
        log.error('Database query error:', error.message);
        throw error;
    }
};

export const getClient = () => pool.connect();

export default pool;
