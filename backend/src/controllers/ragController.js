import {
    validateQueryParams,
    performQuery,
    validateIngestUrls,
    submitDocumentsForIngestion,
    checkJobStatus,
    getUserDocuments,
    checkServiceHealth
} from '../services/ragService.js';
import {
    sendSuccess,
    sendBadRequest,
    sendNotFound,
    sendServiceUnavailable,
    sendGatewayTimeout,
    sendError
} from '../utils/response.js';
import log from '../utils/logger.js';

export const queryRAG = async (req, res) => {
    try {
        const { subject, query: queryText, top_k = 10 } = req.body;
        const userId = req.user.uid;

        const validation = validateQueryParams(queryText, top_k);
        if (!validation.valid) {
            return sendBadRequest(res, validation.message);
        }

        const result = await performQuery(userId, subject, queryText, validation.topK);

        return sendSuccess(res, result);
    } catch (error) {
        log.error('RAG query proxy error:', error.message);

        if (error.message.includes('unavailable')) {
            return sendServiceUnavailable(res, error.message);
        }

        if (error.message.includes('timed out')) {
            return sendGatewayTimeout(res, error.message);
        }

        return sendError(res, 'Failed to query RAG service', 500, error);
    }
};

export const ingestDocuments = async (req, res) => {
    try {
        const userId = req.user.uid;
        const { urls } = req.body;

        const validation = validateIngestUrls(urls);
        if (!validation.valid) {
            return sendBadRequest(res, validation.message);
        }

        const result = await submitDocumentsForIngestion(userId, urls);

        return res.status(202).json({
            success: true,
            message: 'Documents submitted for processing',
            data: {
                jobId: result.jobId,
                status: result.status,
                totalUrls: urls.length,
            },
        });
    } catch (error) {
        log.error('Document ingestion error:', error.message);
        return sendError(res, 'Failed to submit documents for processing', 500, error);
    }
};

export const getJobStatus = async (req, res) => {
    try {
        const { jobId } = req.params;

        const status = await checkJobStatus(jobId);

        return sendSuccess(res, status);
    } catch (error) {
        if (error.message.includes('not found')) {
            return sendNotFound(res, 'Job not found');
        }

        log.error('Status check error:', error.message);
        return sendError(res, 'Failed to check job status', 500, error);
    }
};

export const getDocuments = async (req, res) => {
    try {
        const userId = req.user.uid;

        const documents = await getUserDocuments(userId);

        return sendSuccess(res, documents);
    } catch (error) {
        log.error('Fetch documents error:', error);
        return sendError(res, 'Failed to fetch user documents', 500, error);
    }
};

export const healthCheck = async (req, res) => {
    try {
        const isHealthy = await checkServiceHealth();

        if (isHealthy) {
            return sendSuccess(res, { status: 'online' }, 'RAG service is healthy');
        }

        return sendServiceUnavailable(res, 'RAG service is unavailable');
    } catch (error) {
        log.error('RAG health check error:', error.message);
        return sendServiceUnavailable(res, 'RAG service health check failed');
    }
};
