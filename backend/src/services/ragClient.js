import axios from 'axios';
import config from '../config/index.js';

// Configure axios instance with defaults
const ragAxios = axios.create({
    baseURL: config.ragUrl,
    timeout: 30000, // 30 second timeout
    headers: {
        'Content-Type': 'application/json',
    },
});

// Retry configuration
const MAX_RETRIES = 3;
const RETRY_DELAY = 1000; // 1 second

/**
 * Helper function to retry failed requests
 */
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

            console.warn(`RAG request failed (attempt ${i + 1}/${retries}), retrying...`);
            await new Promise(resolve => setTimeout(resolve, RETRY_DELAY * (i + 1)));
        }
    }
};

/**
 * Query RAG service for Past Year Questions
 * @param {string} subject - Subject name (e.g., "Data Structures", "Algorithms")
 * @param {string} queryText - Natural language query or topic
 * @param {number} topK - Number of results to return (default: 10)
 * @returns {Promise<Object>} RAG response with results and analysis
 */
export const queryPYQs = async (subject, queryText, topK = 10) => {
    try {
        console.log(`Querying RAG for subject: ${subject}, query: ${queryText}`);

        const response = await retryRequest(async () => {
            return await ragAxios.post('/query', {
                subject,
                query: queryText,
                top_k: topK,
            });
        });

        console.log(`RAG query successful, ${response.data.results?.length || 0} results returned`);

        return {
            success: true,
            results: response.data.results || [],
            analysis: response.data.analysis || {},
            metadata: {
                subject,
                query: queryText,
                topK,
                timestamp: new Date().toISOString(),
            },
        };
    } catch (error) {
        console.error(' RAG query error:', error.message);

        // Check if RAG service is unavailable
        if (error.code === 'ECONNREFUSED') {
            throw new Error('RAG service is unavailable. Please ensure the service is running.');
        }

        if (error.code === 'ETIMEDOUT') {
            throw new Error('RAG service request timed out. Please try again.');
        }

        if (error.response) {
            throw new Error(`RAG service error: ${error.response.data?.message || error.response.statusText}`);
        }

        throw new Error(`Failed to query RAG service: ${error.message}`);
    }
};

/**
 * Trigger RAG service to ingest PDFs for a specific year
 * @param {string|number} year - Academic year (e.g., "2024", "2024-2025")
 * @param {string} folderPath - Path to folder containing PDFs
 * @returns {Promise<Object>} Ingestion status and statistics
 */
export const ingestYear = async (year, folderPath) => {
    try {
        console.log(`Starting ingestion for year ${year} from path: ${folderPath}`);

        const response = await retryRequest(async () => {
            return await ragAxios.post(
                '/ingest',
                {
                    year: String(year),
                    folder_path: folderPath,
                },
                {
                    timeout: 300000, // 5 minute timeout for ingestion
                }
            );
        });

        console.log(`Ingestion completed for year ${year}`);

        return {
            success: true,
            year,
            statistics: response.data.statistics || {},
            message: response.data.message || 'Ingestion completed successfully',
        };
    } catch (error) {
        console.error(` RAG ingestion error for year ${year}:`, error.message);

        if (error.code === 'ECONNREFUSED') {
            throw new Error('RAG service is unavailable. Please ensure the service is running.');
        }

        if (error.code === 'ETIMEDOUT') {
            throw new Error('RAG ingestion timed out. This may be normal for large datasets.');
        }

        if (error.response) {
            throw new Error(`RAG ingestion error: ${error.response.data?.message || error.response.statusText}`);
        }

        throw new Error(`Failed to ingest year ${year}: ${error.message}`);
    }
};

/**
 * Check RAG service health
 * @returns {Promise<boolean>} True if service is healthy
 */
export const checkHealth = async () => {
    try {
        const response = await ragAxios.get('/health', { timeout: 5000 });
        return response.status === 200 && response.data?.ok === true;
    } catch (error) {
        console.warn('RAG service health check failed:', error.message);
        return false;
    }
};

/**
 * Get RAG service statistics
 * @returns {Promise<Object>} Service statistics (document count, collections, etc.)
 */
export const getStatistics = async () => {
    try {
        const response = await ragAxios.get('/stats');
        return {
            success: true,
            stats: response.data,
        };
    } catch (error) {
        console.error(' Failed to get RAG statistics:', error.message);
        throw new Error(`Failed to get RAG statistics: ${error.message}`);
    }
};

export default {
    queryPYQs,
    ingestYear,
    checkHealth,
    getStatistics,
};
