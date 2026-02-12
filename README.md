# ExamIntel

AI-powered academic recovery using PYQ intelligence for students.

#AMUHACKS5.0 #CSSAMU #CSDAMU #AMU

---

## Table of Contents

- [Overview](#overview)
- [Team Details](#team-details)
- [Problem Statement](#problem-statement)
- [Solution Architecture](#solution-architecture)
- [Technologies Used](#technologies-used)
- [RAG Pipeline](#rag-pipeline)
- [API Endpoints](#api-endpoints)
- [Setup & Deployment](#setup--deployment)
- [Innovation & Uniqueness](#innovation--uniqueness)
- [Scalability](#scalability)
- [Expected Impact](#expected-impact)

---

## Overview

ExamIntel is an AI-powered academic recovery system that transforms **15 years of AMU Past Year Questions (PYQs)** into personalized study plans. Using **RAG (Retrieval-Augmented Generation)** with Google Gemini AI, the system analyzes historical exam patterns and creates optimized recovery plans tailored to each student's gaps, deadlines, and learning style.

### Key Features

- **Smart Assessment**: 6-7 targeted questions to understand student gaps and constraints
- **PYQ Intelligence**: Semantic search across 15 years of AMU PYQs (2010-2025)
- **AI-Powered Analysis**: Google Gemini identifies topic frequencies and exam patterns
- **Multi-Factor Planning**: Priority scoring based on PYQ frequency, marks weightage, and student gaps
- **Personalized Dashboard**: Daily schedules, priority topics, and exam strategies
- **100% Self-Hosted**: Full Docker containerization with no vendor lock-in

---

## Team Details

**Team Name:** The Build Guild

**Team Members:**
1. Sandipan Singh
2. Zulekha Aalmi
3. Ashutosh Jha
4. Karman Singh Chandhok

**Problem Statement:** PS-03 - AMU Academic Recovery Engine  
**Hackathon:** AMUHACKS5.0

---

## Problem Statement

### The Core Challenge

Students struggle with academic recovery due to:

- **Generic study plans** that ignore individual gaps
- **No exam pattern intelligence** - 70% of questions repeat from PYQs
- **Poor time management** with multiple subjects and tight deadlines
- **Lack of personalization** for learning pace and stress levels

### The Opportunity

15 years of AMU PYQs (2010-2025) contain predictable patterns, yet students study blindly without this intelligence. Our solution transforms historical exam data into personalized, actionable recovery plans.

---

## Solution Architecture

### High-Level System Architecture

```mermaid
graph TB
    A[AMU Student] -->|1. Google OAuth| B[React Frontend]
    
    B -->|2. Assessment data| C[Backend API<br/>Node.js + Express]
    
    C -->|3. Query| D[RAG Engine]
    
    D -->|4. Semantic search| E[(Qdrant Vector DB<br/>15 years PYQs)]
    
    D -->|5. Analyze patterns| F[Google Gemini AI<br/>Pattern Analysis]
    
    F -->|6. Intelligence| G[Planning Algorithm<br/>Priority + Schedule]
    
    G -->|7. Recovery plan| B
    
    C -.->|Store| H[(PostgreSQL)]
    C -.->|Cache| I[(Redis)]
    C -.->|Verify auth| J[Firebase Admin SDK]
    
    subgraph "Docker Compose Environment"
        B
        C
        E
        H
        I
    end
    
    style D fill:#e1f5ff
    style F fill:#ffe1f5
    style G fill:#fff4e1
```

### Complete Workflow

```mermaid
sequenceDiagram
    participant Student
    participant Frontend as React Frontend
    participant Firebase as Firebase Auth
    participant API as Backend API
    participant AdminSDK as Firebase Admin SDK
    participant RAG as RAG Engine
    participant VDB as Qdrant Vector DB
    participant Gemini as Google Gemini AI
    participant DB as PostgreSQL

    Student->>Frontend: 1. Click "Login with Google"
    Frontend->>Firebase: 2. Initiate Google OAuth
    Firebase-->>Frontend: 3. ID Token + User Info

    Frontend->>API: 4. Send ID Token (Bearer)
    API->>AdminSDK: 5. Verify ID Token
    AdminSDK-->>API: 6. Token Validated + UID
    API->>DB: 7. Upsert User Profile
    DB-->>API: 8. User Record Ready
    API-->>Frontend: 9. Auth Success
    Frontend-->>Student: 10. Redirect to Dashboard

    rect rgb(240,248,255)
        Note over Student,DB: Assessment & Plan Generation
        Student->>Frontend: 11. Submit 6-7 answers
        Frontend->>API: 12. POST assessment + Bearer Token
        API->>AdminSDK: 13. Verify Token
        AdminSDK-->>API: 14. Valid
        
        API->>RAG: 15. Query PYQs for subjects
        RAG->>VDB: 16. Semantic search
        VDB-->>RAG: 17. Relevant PYQs (2010-2025)
        
        RAG->>Gemini: 18. Analyze patterns
        Gemini-->>RAG: 19. Topic frequency + insights
        
        RAG-->>API: 20. PYQ intelligence
        API->>API: 21. Run planning algorithm
        API->>DB: 22. Save recovery plan
        API-->>Frontend: 23. Recovery plan JSON
        Frontend-->>Student: 24. Display personalized dashboard
    end

    rect rgb(240,255,240)
        Note over Frontend,API: Subsequent Requests
        Frontend->>API: API Request + Bearer Token
        API->>AdminSDK: Verify Token
        AdminSDK-->>API: Valid
        API-->>Frontend: Protected Data
    end
```

---

## Technologies Used

### Self-Hosted Docker Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | React + TypeScript | Modern UI framework |
| | Tailwind CSS + shadcn/ui | Responsive design |
| | Vite | Build tool |
| **Backend** | Node.js 18 + Express | RESTful API (ESM modules) |
| | ioredis 5.3.2 | Redis client |
| | express-rate-limit 7.1.5 | Rate limiting |
| | resend 3.0.0 | Email notifications |
| **Databases** | PostgreSQL 16 | User data, assessments, plans |
| | Redis 7 | Query caching, rate limiting |
| | Qdrant (self-hosted) | Vector database for PYQs |
| **Authentication** | Firebase Google OAuth | Secure login |
| | Firebase Admin SDK | Token verification |
| **AI/ML** | Google Gemini 2.0 Flash | LLM analysis & plan generation |
| | Gemini Embedding 001 | Vector embeddings |
| **RAG Service** | Python 3.11 + FastAPI | Document processing |
| | LangChain | Text splitting |
| **Infrastructure** | Docker + Docker Compose | Containerization |
| **Algorithms** | Custom TypeScript/Python | Priority scoring, scheduling |

**Deployment:** 100% self-hosted (except Firebase Auth & Gemini API)

---

## RAG Pipeline

### Architecture

```mermaid
graph TD
    subgraph "One-Time Setup"
        A["AMU PYQ PDFs (2010-2025)"] -->|1. Parse text| B[PDF Processor]
        B -->|2. Chunk 500 tokens| C[Text Splitter]
        C -->|3. Add metadata| D[Enrichment]
        D -->|4. Generate embeddings| E[Gemini Embedding API]
        E -->|5. Store vectors| F["Qdrant Vector DB (Self-hosted)"]
    end
    
    subgraph "Runtime Query"
        G["Student Query: Data Structures"] -->|6. Embed query| H[Gemini Embedding]
        H -->|7. Similarity search| F
        F -->|8. Top results| I[Retrieved PYQs]
        I -->|9. Context| J[Gemini AI Analysis]
        J -->|10. JSON output| K[Topic Frequency & Strategy]
    end
    
    style F fill:#4a90e2,color:#fff
    style J fill:#f39c12,color:#fff
    style K fill:#2ecc71,color:#fff
```

### Planning Algorithm

**Multi-Factor Priority Scoring:**

```
Priority Score = (PYQ_Frequency × Avg_Marks × Understanding_Gap × Stress_Factor) 
                 ÷ (Current_Coverage + 0.1)
```

**Example: Data Structures Topics**

| Topic | PYQ Freq | Avg Marks | Student Gap | Priority | Rank |
|-------|----------|-----------|-------------|----------|------|
| Binary Trees | 12/15 | 12 | 6/10 | 144.0 | #1 |
| Graphs | 10/15 | 15 | 5/10 | 125.0 | #2 |
| Dynamic Programming | 8/15 | 10 | 7/10 | 112.0 | #3 |
| Sorting | 6/15 | 8 | 4/10 | 48.0 | #4 |

**Outcome:** System prioritizes Binary Trees first → Maximum ROI for limited study time

---

## API Endpoints

### Base URL
```
http://localhost:8000/api
```

### Authentication

#### POST `/api/auth/verify`
Verify Firebase ID token and create/update user.

**Request:**
```json
{
  "idToken": "firebase-jwt-token"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Token verified successfully",
  "data": {
    "id": "user-id",
    "email": "user@example.com",
    "name": "User Name",
    "createdAt": "2024-01-01T00:00:00.000Z"
  }
}
```

#### GET `/api/auth/me`
Get current authenticated user info.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "user-id",
    "email": "user@example.com",
    "name": "User Name",
    "createdAt": "2024-01-01T00:00:00.000Z"
  }
}
```

---

### Assessments

#### POST `/api/assessment/submit`
Submit assessment answers and generate recovery plan.

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "answers": {
    "q1": {
      "subject": "Data Structures",
      "topic": "Trees",
      "confidence": 3,
      "correctness": "incorrect"
    }
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Assessment submitted and plan generated",
  "data": {
    "assessmentId": "uuid",
    "plan": { ... }
  }
}
```

#### GET `/api/assessment/:id`
Get specific assessment by ID.

**Headers:** `Authorization: Bearer <token>`

#### GET `/api/assessment/user/history`
Get all assessments for current user.

**Headers:** `Authorization: Bearer <token>`

---

### Recovery Plans

#### GET `/api/plan/:planId`
Get recovery plan by ID.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "userId": "user-id",
    "assessmentId": "uuid",
    "plan": {
      "summary": { ... },
      "topics": [ ... ],
      "schedule": [ ... ]
    },
    "createdAt": "2024-01-01T00:00:00.000Z"
  }
}
```

#### POST `/api/plan/save`
Save a recovery plan.

**Headers:** `Authorization: Bearer <token>`

#### GET `/api/plan/user/history`
Get all recovery plans for current user.

**Headers:** `Authorization: Bearer <token>`

#### PUT `/api/plan/:planId`
Update existing recovery plan.

**Headers:** `Authorization: Bearer <token>`

---

### RAG Service Proxy

#### POST `/api/rag/query`
Query RAG service for PYQ questions.

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "subject": "Data Structures",
  "query": "binary search tree questions",
  "top_k": 10
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "results": [
      {
        "text": "Question text...",
        "score": 0.92,
        "metadata": { "year": 2023, "topic": "BST" }
      }
    ],
    "analysis": {
      "topics": ["BST", "Traversal"],
      "insights": "..."
    }
  }
}
```

#### POST `/api/rag/ingest`
Submit PDF URLs for ingestion.

**Headers:** `Authorization: Bearer <token>`

**Request:**
```json
{
  "urls": [
    "https://example.com/pyq2023.pdf",
    "https://example.com/pyq2022.pdf"
  ]
}
```

#### GET `/api/rag/jobs/:jobId`
Check ingestion job status.

**Headers:** `Authorization: Bearer <token>`

#### GET `/api/rag/documents`
Get all documents for current user.

**Headers:** `Authorization: Bearer <token>`

#### GET `/api/rag/health`
Check RAG service health.

**Response:**
```json
{
  "success": true,
  "message": "RAG service is healthy",
  "data": {
    "status": "online"
  }
}
```

---

### Response Format

**Success:**
```json
{
  "success": true,
  "message": "Operation successful",
  "data": { ... }
}
```

**Error:**
```json
{
  "success": false,
  "error": "Error Type",
  "message": "Human-readable error message"
}
```

**HTTP Status Codes:**
- `200` - Success
- `201` - Created
- `400` - Bad Request (validation errors)
- `401` - Unauthorized (invalid/expired token)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found
- `409` - Conflict (duplicate resource)
- `500` - Internal Server Error
- `503` - Service Unavailable (RAG service down)
- `504` - Gateway Timeout

---

## Setup & Deployment

### Prerequisites

- Docker & Docker Compose
- Firebase project (for Google OAuth)
- Google Gemini API key

### Environment Configuration

Create `.env` file in project root:

```bash
# Backend
PORT=8000
NODE_ENV=development
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/examintel_db

# Firebase
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_CREDENTIALS_JSON='{"type":"service_account",...}'

# RAG Service
RAG_URL=http://rag:8001
GEMINI_API_KEY=your-gemini-api-key

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_ENABLED=true
CACHE_TTL=3600

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_WINDOW_MS=60000
RATE_LIMIT_MAX_REQUESTS=100

# Email
RESEND_API_KEY=your-resend-api-key
EMAIL_FROM=noreply@examintel.com

# CORS
CORS_ORIGINS=http://localhost:3000
CORS_ALLOW_CREDENTIALS=true

# Qdrant
QDRANT_HOST=qdrant
QDRANT_PORT=6333
```

### Quick Start with Docker

```bash
# Clone repository
git clone <repository-url>
cd TheBuildGuild_AMUHACKS5.0

# Create .env file (see above)
cp .env.example .env

# Start all services
docker compose up -d --build

# Check service health
docker compose ps

# View logs
docker compose logs -f backend
docker compose logs -f rag
```

**Services will be available at:**
- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- PostgreSQL: `localhost:5432`
- Qdrant Dashboard: `http://localhost:6333/dashboard`

### Manual Setup (Development)

**Backend:**
```bash
cd backend
npm install
npm run dev  # Runs on port 8000
```

**Frontend:**
```bash
cd client
npm install
npm run dev  # Runs on port 3000
```

**RAG Service:**
```bash
cd rag
pip install -r requirements.txt
uvicorn src.app:app --reload --port 8001
```

### Database Initialization

```bash
# Connect to PostgreSQL
docker compose exec postgres psql -U postgres -d examintel_db

# Run migrations
\i /docker-entrypoint-initdb.d/init.sql
```

---

## Innovation & Uniqueness

### What Sets Us Apart

**1. RAG-Powered PYQ Intelligence**
- First system to semantically search 15 years of AMU PYQs
- AI-driven pattern detection via Gemini (not just storage)
- "Trees appeared in 12/15 papers" → Direct study priorities

**2. AMU-First, Then Universal**
- **Now:** Exclusive focus on AMU students with real AMU data
- **Future:** Any student uploads their college PYQs → Instant intelligence
- Scalable multi-tenant architecture ready

**3. 100% Self-Hosted Control**
- Full Docker containerization - no vendor lock-in
- Own your data, own your infrastructure
- Easy deployment anywhere

**4. Multi-Constraint Optimization**
- Balances: PYQ patterns + deadlines + stress + learning pace
- Not generic advice - contextual, mathematical prioritization

**5. Conversational Intelligence**
- 6-7 questions → Complete plan (vs. 30+ field forms)
- Gemini AI matches resources to learning style

---

## Scalability

### Phase 1: AMU Students Only (Current)

**Target:** 500 AMU students  
**Infrastructure:** Single Docker Compose stack  
**Data:** 100+ AMU PYQs (2010-2025)

### Phase 2: Universal Platform (Future)

**Vision:** Any student, any college can use the system

**Key Features:**
- Student self-service PYQ upload
- Auto-detection of subjects, topics
- College-specific exam strategy
- Scalable to 100+ universities

**Infrastructure Scaling Path:**

| Users | Setup | Strategy |
|-------|-------|----------|
| 0-500 | Docker Compose | Single server |
| 500-5K | Multi-container | Horizontal scaling + load balancer |
| 5K+ | Kubernetes | Microservices architecture |

---

## Expected Impact

### Immediate Impact (AMU Students)

**Quantitative Results:**
- ⏱️ **80% time saved** in study planning (6 hours → 45 minutes)
- 🎯 **35% score improvement** via PYQ-focused preparation
- 📚 **90% syllabus coverage** (vs. 60% with generic plans)

**Qualitative Benefits:**
- Reduced exam anxiety through structure
- Data-driven confidence: "12 PYQs on Trees → I'm ready"
- Optimized effort-to-marks ratio

### Long-Term Vision

**Democratizing Exam Intelligence**

**Year 1:** AMU deployment → 500 students  
**Year 2:** Launch "Upload Your PYQs" → 10 colleges  
**Year 3:** National platform → 50,000+ students

**Research Impact:**
- Largest PYQ intelligence database in India
- Insights for curriculum optimization
- Open-source academic recovery framework

---

## Project Structure

```
TheBuildGuild_AMUHACKS5.0/
├── backend/                 # Node.js + Express API
│   ├── src/
│   │   ├── server.js       # Entry point
│   │   ├── app.js          # Express app setup
│   │   ├── config/         # Environment configuration
│   │   ├── controllers/    # Request handlers
│   │   ├── middleware/     # Auth, rate limiting
│   │   ├── routes/         # API endpoints
│   │   ├── services/       # Business logic
│   │   ├── db/             # Database clients
│   │   └── utils/          # Utilities
│   └── package.json
├── client/                  # React + TypeScript frontend
│   ├── src/
│   │   ├── pages/          # Route components
│   │   ├── components/     # Reusable UI
│   │   ├── context/        # Auth context
│   │   ├── api/            # API client
│   │   └── config/         # Firebase config
│   └── package.json
├── rag/                     # Python + FastAPI RAG service
│   ├── src/
│   │   ├── app.py          # FastAPI app
│   │   ├── api/routes/     # RAG endpoints
│   │   ├── services/       # Embedding, ingestion
│   │   ├── pipelines/      # Ingest pipeline
│   │   ├── clients/        # Gemini, Qdrant, Redis
│   │   └── models/         # Data models
│   └── requirements.txt
├── db/
│   └── init.sql            # PostgreSQL schema
├── docs/                    # Documentation
│   ├── PRD.md
│   ├── WORKFLOW.md
│   ├── IMPLEMENTATION.md
│   └── BACKEND_SCHEMA.md
├── docker-compose.yml       # Service orchestration
├── Dockerfile.backend
├── Dockerfile.rag
└── README.md
```

---

## Documentation

- [Product Requirements Document](docs/PRD.md)
- [Workflow Diagrams](docs/WORKFLOW.md)
- [Implementation Guide](docs/IMPLEMENTATION.md)
- [Backend Schema](docs/BACKEND_SCHEMA.md)
- [Document Upload Guide](docs/DOCUMENT_UPLOAD_GUIDE.md)
- [Tech Stack Details](docs/TECHSTACK.md)

---

## License

[MIT License](LICENSE)

---

## Contact

**Team: The Build Guild**  
**Hackathon:** AMUHACKS5.0  
**Problem Statement:** PS-03

---

**Built with ❤️ for AMU students**
