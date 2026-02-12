import axios from 'axios';
import { query } from '../db/pgClient.js';
import config from '../config/index.js';
import log from '../utils/logger.js';

const ragAxios = axios.create({
    baseURL: config.ragUrl,
    headers: {
        'Content-Type': 'application/json',
    },
});

const MAX_RETRIES = 3;
const RETRY_DELAY = 1000;

const retryRequest = async (fn, retries = MAX_RETRIES) => {
    for (let i = 0; i < retries; i++) {
        try {
            return await fn();
        } catch (error) {
            const isLastRetry = i === retries - 1;
            const isRetriableError =
                error.code === 'ECONNREFUSED' ||
                error.code === 'ETIMEDOUT' ||
                (error.response && error.response.status >= 500);

            if (isLastRetry || !isRetriableError) {
                throw error;
            }

            log.warn(`RAG request failed (attempt ${i + 1}/${retries}), retrying...`);
            await new Promise(resolve => setTimeout(resolve, RETRY_DELAY * (i + 1)));
        }
    }
};

export const validateQueryParams = (queryText, topK) => {
    if (!queryText) {
        return { valid: false, message: 'query is required' };
    }

    const parsedTopK = parseInt(topK, 10);
    if (isNaN(parsedTopK) || parsedTopK < 1 || parsedTopK > 50) {
        return { valid: false, message: 'top_k must be between 1 and 50' };
    }

    return { valid: true, topK: parsedTopK };
};

export const performQuery = async (userId, subject, queryText, topK) => {
    try {
        log.debug(`Querying RAG - user: ${userId}, subject: ${subject}, query: ${queryText}`);

        const response = await retryRequest(async () => {
            return await ragAxios.post('/api/v1/query', {
                user_id: userId,
                subject: subject || null,
                query: queryText,
                top_k: topK,
            });
        });

        log.success(`RAG query successful, ${response.data.results?.length || 0} results returned`);

        return {
            success: true,
            results: response.data.results || [],
            analysis: response.data.analysis || {},
        };
    } catch (error) {
        log.error('RAG query error:', error.message);

        if (error.code === 'ECONNREFUSED') {
            throw new Error('RAG service is unavailable');
        }

        if (error.code === 'ETIMEDOUT') {
            throw new Error('RAG service request timed out');
        }

        if (error.response) {
            throw new Error(error.response.data?.message || error.response.statusText);
        }

        throw new Error(`RAG service error: ${error.message}`);
    }
};

export const validateIngestUrls = (urls) => {
    if (!urls || !Array.isArray(urls) || urls.length === 0) {
        return { valid: false, message: 'Please provide an array of PDF URLs' };
    }

    return { valid: true };
};

export const submitDocumentsForIngestion = async (userId, urls) => {
    try {
        log.info(`Ingesting ${urls.length} documents for user ${userId}`);

        const response = await ragAxios.post('/api/v1/ingest/url', {
            user_id: userId,
            urls,
        });

        log.success(`Ingestion job created: ${response.data.job_id}`);

        return {
            success: true,
            jobId: response.data.job_id,
            status: response.data.status,
        };
    } catch (error) {
        log.error('Document ingestion error:', error.message);
        throw new Error(`Failed to ingest documents: ${error.message}`);
    }
};

export const checkJobStatus = async (jobId) => {
    try {
        const response = await ragAxios.get(`/api/v1/ingest/status/${jobId}`);
        return response.data;
    } catch (error) {
        log.error('Get job status error:', error.message);
        throw new Error(`Failed to get job status: ${error.message}`);
    }
};

export const getUserDocuments = async (userId) => {
    const sql = `
        SELECT 
            d.id,
            d.sha256_hash,
            d.original_filename,
            d.total_pages,
            d.upload_source,
            d.source_url,
            d.status,
            d.created_at,
            ud.linked_at,
            COUNT(dc.id) as chunk_count
        FROM documents d
        JOIN user_documents ud ON d.sha256_hash = ud.document_sha256
        LEFT JOIN document_chunks dc ON d.sha256_hash = dc.document_sha256
        WHERE ud.user_id = $1
        GROUP BY d.id, d.sha256_hash, d.original_filename, d.total_pages, 
                 d.upload_source, d.source_url, d.status, d.created_at, ud.linked_at
        ORDER BY ud.linked_at DESC
    `;

    const result = await query(sql, [userId]);
    return result.rows;
};

export const checkServiceHealth = async () => {
    try {
        const response = await ragAxios.get('/health', { timeout: 5000 });
        return response.status === 200 && response.data?.status === 'ok';
    } catch (error) {
        log.warn('RAG service health check failed:', error.message);
        return false;
    }
};

export const getServiceStats = async () => {
    try {
        const response = await ragAxios.get('/api/v1/ingest/stats', { timeout: 5000 });
        return response.data;
    } catch (error) {
        log.warn('RAG service stats check failed:', error.message);
        throw error;
    }
};
