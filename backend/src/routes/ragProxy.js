import express from 'express';
import { queryPYQs, ingestYear, checkHealth } from '../services/ragClient.js';
import authMiddleware from '../middleware/authMiddleware.js';

const router = express.Router();

/**
 * POST /api/rag/query
 * Query RAG service for Past Year Questions
 */
router.post('/query', async (req, res) => {
    try {
        const { subject, query, top_k = 10 } = req.body;

        // Validate input
        if (!subject || !query) {
            return res.status(400).json({
                error: 'Bad Request',
                message: 'subject and query are required',
            });
        }

        // Validate top_k
        const topK = parseInt(top_k, 10);
        if (isNaN(topK) || topK < 1 || topK > 50) {
            return res.status(400).json({
                error: 'Bad Request',
                message: 'top_k must be between 1 and 50',
            });
        }

        // Query RAG service
        const result = await queryPYQs(subject, query, topK);

        return res.status(200).json({
            success: true,
            data: result,
        });
    } catch (error) {
        console.error('RAG query proxy error:', error);

        // Check for specific error messages
        if (error.message.includes('unavailable')) {
            return res.status(503).json({
                error: 'Service Unavailable',
                message: error.message,
            });
        }

        if (error.message.includes('timed out')) {
            return res.status(504).json({
                error: 'Gateway Timeout',
                message: error.message,
            });
        }

        return res.status(500).json({
            error: 'Internal Server Error',
            message: 'Failed to query RAG service',
        });
    }
});

/**
 * POST /api/rag/ingest
 * Trigger PDF ingestion for a specific year (protected route)
 */
router.post('/ingest', authMiddleware, async (req, res) => {
    try {
        const { year, folder_path } = req.body;

        // Validate input
        if (!year || !folder_path) {
            return res.status(400).json({
                error: 'Bad Request',
                message: 'year and folder_path are required',
            });
        }

        // Validate year format
        const yearStr = String(year);
        if (!/^\d{4}(-\d{4})?$/.test(yearStr)) {
            return res.status(400).json({
                error: 'Bad Request',
                message: 'year must be in format YYYY or YYYY-YYYY',
            });
        }

        console.log(`User ${req.user.uid} triggered ingestion for year ${year}`);

        // Trigger ingestion
        const result = await ingestYear(year, folder_path);

        return res.status(200).json({
            success: true,
            message: `Ingestion completed for year ${year}`,
            data: result,
        });
    } catch (error) {
        console.error('RAG ingest proxy error:', error);

        if (error.message.includes('unavailable')) {
            return res.status(503).json({
                error: 'Service Unavailable',
                message: error.message,
            });
        }

        if (error.message.includes('timed out')) {
            return res.status(202).json({
                success: true,
                message: 'Ingestion started but may still be in progress',
                note: 'Large datasets may take several minutes to complete',
            });
        }

        return res.status(500).json({
            error: 'Internal Server Error',
            message: 'Failed to trigger ingestion',
        });
    }
});

/**
 * GET /api/rag/health
 * Check RAG service health status
 */
router.get('/health', async (req, res) => {
    try {
        const isHealthy = await checkHealth();

        if (isHealthy) {
            return res.status(200).json({
                success: true,
                message: 'RAG service is healthy',
                status: 'online',
            });
        } else {
            return res.status(503).json({
                success: false,
                message: 'RAG service is unavailable',
                status: 'offline',
            });
        }
    } catch (error) {
        console.error('RAG health check error:', error);
        return res.status(503).json({
            success: false,
            message: 'RAG service health check failed',
            status: 'unknown',
        });
    }
});

export default router;
