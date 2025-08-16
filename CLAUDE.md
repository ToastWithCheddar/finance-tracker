
# CLAUDE.md - Memory Bridge for Finance Tracker Execution

## Project Mission & Core Philosophy

**Mission:** Build a modern, production-grade personal finance application that helps users track all financial activity, set and achieve savings goals, manage budgets, and receive clear, explainable, and actionable AI-powered insights about their spending.

### Core Product Philosophy (Non-Negotiable)

- **User empowerment**: All automatic AI/ML suggestions are overrideable, with clear explanations
- **Transparency**: No "black box" features—ML confidence and reasoning are visible to the user
- **Privacy-first**: No sensitive data leaves user's system unless explicit
- **Accessibility and Joy**: Clean, minimal UI; dark/light modes; blur for public spaces; all critical flows keyboard-accessible
- **Automate the boring**: ML, OCR, and auto-categorization should reduce, not increase, manual entry

**Budget:** $0 (free tiers only) | **Timeline:** 30-day development plan | **Target:** Production-ready PWA

---

## System Architecture & Service Responsibilities

### Microservices Pattern (Dockerized)

```
Frontend: React 18 + TypeScript + Vite + Tailwind CSS + Zustand + React Query
Backend API: FastAPI + SQLAlchemy + PostgreSQL + Redis + Nginx (reverse proxy)
ML Worker: Sentence Transformers + ONNX + Celery for distributed ML tasks
Auth: Supabase (user management/auth provider)
External: Plaid (banking) + SendGrid (email) + OpenAI API (optional, not required)
Infrastructure: Docker Compose orchestrates everything
```

### Docker Services & Responsibilities

- **frontend** (React + Nginx): All UX; real-time sync via WebSocket; offline/optimistic updates
- **backend** (FastAPI + Uvicorn + WebSocket): REST/WS API; business logic; all DB ops; ML service integration
- **postgres** (PostgreSQL 15): Source of truth for financial/accounting data
- **redis** (Redis): Message queue (Celery), real-time cache (WebSocket), ephemeral store
- **ml-worker** (Sentence Transformers + Classification): Transaction categorization; learns from user feedback
- **nginx** (Reverse proxy + WebSocket): Single public entrypoint; routes requests; rate-limits API/auth

**Important**: Single environment only - no suffixes/prefixes for variables. All production and development systems point to the same thing.

---

## Actual Project Structure & File Navigation

### Backend Structure (`backend/`)

```
app/
├── auth/                    # Authentication system
│   ├── auth_service.py     # Core auth logic with Supabase integration
│   ├── dependencies.py    # FastAPI dependencies for auth
│   ├── middleware.py      # Auth middleware
│   └── supabase_client.py # Supabase client configuration
├── core/                   # Core infrastructure
│   ├── exceptions.py      # Custom exception classes
│   ├── import_standards.md # Code standards documentation
│   └── redis_client.py    # Redis connection management
├── routes/                 # API endpoints (all REST routes)
│   ├── accounts.py        # Account CRUD and Plaid integration
│   ├── analytics.py       # Analytics and reporting endpoints
│   ├── auth.py           # Authentication endpoints
│   ├── budget.py         # Budget management endpoints
│   ├── categories.py     # Category management
│   ├── goals.py          # Goal tracking endpoints
│   ├── health.py         # Health check endpoints
│   ├── insights.py       # AI insights endpoints
│   ├── ml.py             # ML model management
│   ├── mlcategory.py     # ML categorization endpoints
│   ├── recurring.py      # Recurring transaction detection
│   ├── transaction.py    # Transaction CRUD operations
│   ├── user.py           # User management
│   └── websockets.py     # WebSocket connection handling
├── schemas/               # Pydantic models for API validation
│   ├── account.py        # Account validation schemas
│   ├── auth.py           # Authentication schemas
│   ├── base.py           # Base schema classes
│   ├── budget.py         # Budget validation schemas
│   ├── category.py       # Category schemas
│   ├── goal.py           # Goal validation schemas
│   ├── transaction.py    # Transaction validation schemas
│   └── user.py           # User schemas
├── services/              # Business logic layer
│   ├── account_service.py           # Account business logic
│   ├── analytics_service.py        # Analytics calculations
│   ├── budget_service.py           # Budget management logic
│   ├── category_service.py         # Category management
│   ├── enhanced_plaid_service.py   # Plaid integration service
│   ├── goal_service.py             # Goal tracking logic
│   ├── ml_client.py                # ML service client
│   ├── transaction_service.py      # Transaction business logic
│   ├── user_service.py             # User management
│   └── recurring_detection_service.py # Recurring pattern detection
├── websocket/             # Real-time WebSocket system
│   ├── events.py         # WebSocket event definitions
│   ├── manager.py        # WebSocket connection manager
│   └── schemas.py        # WebSocket message schemas
├── config.py             # Application configuration
├── database.py           # Database connection setup
├── main.py               # FastAPI application entry point
└── seed_data.py          # Database seeding for development
```

### Frontend Structure (`frontend/src/`)

```
components/
├── accounts/              # Account management components
│   ├── AccountsList.tsx          # Account overview display
│   ├── AccountSyncStatus.tsx     # Plaid sync status indicator
│   └── AccountReconciliation.tsx # Balance reconciliation UI
├── auth/                  # Authentication UI
│   ├── LoginForm.tsx             # Login interface
│   └── RegisterForm.tsx          # Registration interface
├── budgets/               # Budget management UI
│   ├── BudgetCard.tsx           # Individual budget display
│   └── BudgetForm.tsx           # Budget creation/editing
├── dashboard/             # Main dashboard components
│   ├── RealtimeDashboard.tsx     # Main dashboard container
│   ├── RealtimeTransactionFeed.tsx # Live transaction updates
│   ├── CategoryPieChart.tsx      # Category spending visualization
│   ├── SpendingTrendsChart.tsx   # Spending trend analysis
│   ├── MonthlyComparisonChart.tsx # Period comparisons
│   └── NotificationPanel.tsx     # Real-time notifications
├── goals/                 # Goal tracking UI
│   ├── GoalCard.tsx             # Individual goal display
│   ├── GoalDashboard.tsx        # Goals overview
│   └── GoalForm.tsx             # Goal creation/editing
├── transactions/          # Transaction management UI
│   ├── TransactionList.tsx      # Transaction display with filtering
│   ├── TransactionForm.tsx      # Transaction creation/editing
│   ├── TransactionFilters.tsx   # Advanced filtering UI
│   ├── MLCategoryFeedback.tsx   # ML categorization feedback
│   └── CSVImport.tsx            # CSV import functionality
├── plaid/                 # Bank connection UI
│   ├── PlaidLink.tsx            # Plaid Link integration
│   └── AccountConnectionStatus.tsx # Connection status display
└── ui/                    # Reusable UI components
    ├── Button.tsx               # Button component
    ├── Card.tsx                 # Card container
    ├── Modal.tsx                # Modal dialog
    ├── Toast.tsx                # Toast notifications
    └── LoadingSpinner.tsx       # Loading states

hooks/                     # Custom React hooks
├── useTransactions.ts     # Transaction data management
├── useAccounts.ts         # Account data management
├── useBudgets.ts          # Budget data management
├── useGoals.ts            # Goal data management
├── useWebSocket.ts        # WebSocket connection management
└── useDashboard.ts        # Dashboard data aggregation

stores/                    # Zustand state management
├── authStore.ts           # Authentication state
├── realtimeStore.ts       # Real-time data state
└── themeStore.ts          # UI theme preferences

services/                  # API client services
├── api.ts                 # Base API client configuration
├── transactionService.ts  # Transaction API calls
├── accountService.ts      # Account API calls
├── budgetService.ts       # Budget API calls
├── goalService.ts         # Goal API calls
└── mlService.ts           # ML service integration

types/                     # TypeScript type definitions
├── transaction.ts         # Transaction type definitions
├── auth.ts               # Authentication types
├── budgets.ts            # Budget types
├── goals.ts              # Goal types
└── api.ts                # API response types
```

### ML Worker Structure (`ml-worker/`)

```
ml_classification_service.py    # Main ML service with Sentence Transformers
optimized_inference_engine.py  # ONNX-optimized inference engine
onnx_converter.py              # Model conversion utilities
model_monitoring.py            # ML model performance monitoring
ab_testing_framework.py        # A/B testing for ML models
production_orchestrator.py     # Production ML workflow
worker.py                      # Celery worker entry point
```

### Memory 

project-memory/
├── 00-project-overview.md          # High-level project context
├── 01-architecture-decisions.md    # Key technical decisions & rationale
├── 02-codebase-patterns.md         # Code patterns & conventions
├── 03-current-state.md             # What's implemented, what's not
├── 04-dependencies-config.md       # Libraries, tools, setup
└── 05-execution-history.md         # Log of completed tasks

---

## Domain Data Model & Key Files

### Database Models Location

- **SQLAlchemy Models**: Backend database models are likely in `backend/app/models/` (check for model files)
- **Database Migrations**: `backend/migrations/versions/` contains Alembic migration files
- **Schema Definitions**: `backend/app/schemas/` contains Pydantic validation models

### Core Objects (All IDs are UUID4, money as integer cents, UTC timestamps)

**Reference Files for Data Models:**

- **User Model**: `backend/app/schemas/user.py` and corresponding SQLAlchemy model
- **Account Model**: `backend/app/schemas/account.py` and service in `backend/app/services/account_service.py`
- **Transaction Model**: `backend/app/schemas/transaction.py` and service in `backend/app/services/transaction_service.py`
- **Category Model**: `backend/app/schemas/category.py` and service in `backend/app/services/category_service.py`
- **Budget Model**: `backend/app/schemas/budget.py` and service in `backend/app/services/budget_service.py`
- **Goal Model**: `backend/app/schemas/goal.py` and service in `backend/app/services/goal_service.py`

### Relationships & Business Logic

- One user → many accounts, transactions, categories, budgets, goals
- One account → many transactions
- One category → many transactions (hierarchical: parent/child)
- One goal → many contributions/milestones

**Important**: Database entries and relationships can change - always ask user before updating memory when making schema changes.

---

## Critical Technical Decisions & AI/ML System

### ML Pipeline Implementation Files

- **Main ML Service**: `ml-worker/ml_classification_service.py`
- **ONNX Optimization**: `ml-worker/onnx_converter.py` and `ml-worker/optimized_inference_engine.py`
- **ML API Integration**: `backend/app/services/ml_client.py`
- **ML Routes**: `backend/app/routes/ml.py` and `backend/app/routes/mlcategory.py`
- **Category Management**: `backend/app/services/category_service.py`

### ML System Specifications

- **Model**: `all-MiniLM-L6-v2` via Sentence Transformers; ONNX-quantized for <10ms inference on CPU
- **Learning**: Few-shot—category "prototypes" updated by user-corrected examples
- **Confidence Levels**: High (auto-assign), Medium (suggest), Low (ask user)
- **Performance Target**: <10ms inference, >90% accuracy, 75%+ confidence auto-assign

### Real-time System Implementation Files

- **WebSocket Manager**: `backend/app/websocket/manager.py`
- **WebSocket Events**: `backend/app/websocket/events.py`
- **WebSocket Routes**: `backend/app/routes/websockets.py`
- **Frontend WebSocket Hook**: `frontend/src/hooks/useWebSocket.ts`
- **Real-time Store**: `frontend/src/stores/realtimeStore.ts`

---

## Key Service Layer Files & Responsibilities

### Backend Services (`backend/app/services/`)

- **account_service.py**: Account CRUD, balance calculation, Plaid integration
- **transaction_service.py**: Transaction CRUD, categorization, validation
- **budget_service.py**: Budget management, alert system, progress tracking
- **goal_service.py**: Goal tracking, milestone management, progress calculation
- **enhanced_plaid_service.py**: Bank connection, transaction sync, account linking
- **analytics_service.py**: Dashboard analytics, spending analysis, insights generation
- **recurring_detection_service.py**: Automatic recurring transaction detection
- **ml_client.py**: Interface to ML worker service for categorization

### Frontend Services (`frontend/src/services/`)

- **api.ts**: Base API client with authentication and error handling
- **transactionService.ts**: Transaction API calls and local caching
- **accountService.ts**: Account management and Plaid integration
- **budgetService.ts**: Budget API calls and real-time updates
- **goalService.ts**: Goal tracking and progress updates
- **mlService.ts**: ML categorization feedback and suggestions

---

## Configuration & Setup Files

### Key Configuration Files

- **Backend Config**: `backend/app/config.py` - Application settings and environment variables
- **Database Setup**: `backend/app/database.py` - Database connection and session management
- **Docker Compose**: `docker-compose.dev.yml` - Development environment orchestration
- **Frontend Config**: `frontend/vite.config.ts` - Vite build configuration
- **Nginx Config**: `nginx/nginx.conf` - Reverse proxy and routing rules

### Environment & Dependencies

- **Backend Dependencies**: `backend/requirements.txt`, `backend/pyproject.toml`
- **Frontend Dependencies**: `frontend/package.json`
- **ML Worker Dependencies**: `ml-worker/requirements.txt`
- **Environment Template**: `.env.example`

---

## Implementation Status & Key Features

### COMPLETED Features (Based on File Structure)

- Complete Docker infrastructure with all services
- Authentication system with Supabase integration (`backend/app/auth/`)
- **Row-Level Security (RLS) system fully implemented and verified** (`backend/migrations/versions/e98b7b1df196_enable_row_level_security.py`)
- **User context database dependency for secure operations** (`backend/app/auth/dependencies.py::get_db_with_user_context`)
- Transaction management with ML categorization (`backend/app/routes/transaction.py`)
- Account management with Plaid integration (`backend/app/services/enhanced_plaid_service.py`)
- Budget system with real-time tracking (`backend/app/services/budget_service.py`)
- Goal tracking system (`backend/app/services/goal_service.py`)
- Real-time WebSocket system (`backend/app/websocket/`)
- ML classification service with ONNX optimization (`ml-worker/`)
- Frontend dashboard with real-time updates (`frontend/src/components/dashboard/`)
- Recurring transaction detection (`backend/app/services/recurring_detection_service.py`)

### Development Areas to Focus On

- Testing coverage (`backend/tests/`, `frontend/src/__tests__/`)
- Advanced analytics and insights (`backend/app/routes/insights.py`)
- CSV import/export functionality (`frontend/src/components/transactions/CSVImport.tsx`)
- Performance optimization and monitoring
- Security hardening and comprehensive testing

---

## Key Constraints & Non-Negotiable Conventions

### Performance Targets

- ML inference: <10ms per transaction
- WebSocket latency: <100ms for real-time updates
- Dashboard load: <2 seconds initial load
- API response: <200ms for CRUD operations

### Security & Privacy Requirements

- **All API endpoints authenticated** by default (JWT via Supabase)
- **All actions audited** (edit/delete logged by user/timestamp)
- **User data export/delete** flows (GDPR-friendly)
- **Rate limiting**: API (10r/s), Auth (5r/min), via Nginx
- **ML models**: Local inference by default

### Data & Business Rules

- **All money stored as integer cents**; always convert for display
- **All times stored in UTC**, rendered in user's timezone
- **All major user actions auditable**
- **Undo must be available** for all destructive actions
- **Data must be exportable** by user at any time

---

## File Reference Guide for Common Tasks

### When Working on Authentication

- **Backend Auth**: `backend/app/auth/auth_service.py`
- **Auth Routes**: `backend/app/routes/auth.py`
- **Auth Middleware**: `backend/app/auth/middleware.py`
- **Frontend Auth Store**: `frontend/src/stores/authStore.ts`
- **Login Components**: `frontend/src/components/auth/`

### When Working on Transactions

- **Transaction Service**: `backend/app/services/transaction_service.py`
- **Transaction Routes**: `backend/app/routes/transaction.py`
- **Transaction Schemas**: `backend/app/schemas/transaction.py`
- **Frontend Transaction Hook**: `frontend/src/hooks/useTransactions.ts`
- **Transaction Components**: `frontend/src/components/transactions/`

### When Working on ML/Categorization

- **ML Worker**: `ml-worker/ml_classification_service.py`
- **ML Client**: `backend/app/services/ml_client.py`
- **ML Routes**: `backend/app/routes/ml.py`, `backend/app/routes/mlcategory.py`
- **Category Service**: `backend/app/services/category_service.py`
- **Frontend ML Feedback**: `frontend/src/components/transactions/MLCategoryFeedback.tsx`

### When Working on Real-time Features

- **WebSocket Manager**: `backend/app/websocket/manager.py`
- **WebSocket Events**: `backend/app/websocket/events.py`
- **Frontend WebSocket Hook**: `frontend/src/hooks/useWebSocket.ts`
- **Real-time Store**: `frontend/src/stores/realtimeStore.ts`
- **Dashboard Components**: `frontend/src/components/dashboard/`

### When Working on Budget/Goals

- **Budget Service**: `backend/app/services/budget_service.py`
- **Goal Service**: `backend/app/services/goal_service.py`
- **Budget Routes**: `backend/app/routes/budget.py`
- **Goal Routes**: `backend/app/routes/goals.py`
- **Frontend Budget Components**: `frontend/src/components/budgets/`
- **Frontend Goal Components**: `frontend/src/components/goals/`

---

## Quick Reference Commands

### Development Environment

```bash
# Start all services
docker-compose -f docker-compose.yml up -d
# or 
./scripts/dev.sh

# Database migrations  
docker exec backend alembic upgrade head

# Access points
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000  
# API Docs: http://localhost:8000/docs
# Database: localhost:5432
# Redis: localhost:6379
```

---

## Memory Summary for AI Assistant

**Mission**: Help build, improve, and document a modern, explainable, user-first finance tracker. All features, decisions, and code must align with this project context and the domain/business model described here.

**Key Navigation Principle**: Instead of keeping code snippets in memory, always reference the actual files in the project structure. Use this memory as a map to find the right files for any given task.

**File-First Approach**: When implementing features, always check existing implementations in the relevant service/component files before writing new code. The project structure is comprehensive and most patterns already exist.

**If any doubt exists, check the relevant files first, then clarify with the user, and record changes in memory.** This file is living documentation: update it with all significant architectural, business, or model changes.

**Vital** : Don't try to read "repomix-output.xml", without asking for permission