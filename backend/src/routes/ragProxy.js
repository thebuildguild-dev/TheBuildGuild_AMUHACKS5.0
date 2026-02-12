import express from 'express';
import authMiddleware from '../middleware/authMiddleware.js';
import {
    queryRAG,
    ingestDocuments,
    getJobStatus,
    getDocuments,
    healthCheck
} from '../controllers/ragController.js';

const router = express.Router();

router.post('/query', authMiddleware, queryRAG);
router.post('/ingest', authMiddleware, ingestDocuments);
router.get('/jobs/:jobId', authMiddleware, getJobStatus);
router.get('/documents', authMiddleware, getDocuments);
router.get('/health', healthCheck);

export default router;
