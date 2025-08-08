## **Project Mission & Scope**

The Finance Tracker is a modern, production-grade personal finance application.
Its purpose is to **help users track all financial activity, set and achieve savings goals, manage budgets, and receive clear, explainable, and actionable AI-powered insights** about their spending, all in a secure, privacy-conscious, and delightful user experience.

This context file encodes **project architecture, domain model, system conventions, AI/ML design, and collaboration practices** for all contributors and assistant LLMs.

---

### **Core Product Philosophy**

* **User empowerment**: All automatic AI/ML suggestions are overrideable, with clear explanations.
* **Transparency**: No "black box" features—ML confidence and reasoning are visible to the user.
* **Privacy-first**: No sensitive data leaves user's system unless explicit.
* **Accessibility and Joy**: Clean, minimal UI; dark/light modes; blur for public spaces; all critical flows keyboard-accessible.
* **Automate the boring**: ML, OCR, and auto-categorization should reduce, not increase, manual entry.

---

## **High-Level System Architecture**

**Microservices pattern (Dockerized):**

* **Frontend**: React 18 + TypeScript, Tailwind, Zustand, React Query, Recharts, etc.
* **Backend API**: FastAPI, SQLAlchemy, PostgreSQL, Redis, Nginx (reverse proxy)
* **ML Worker**: Sentence Transformers, ONNX-optimized for CPU, Celery for distributed ML tasks, feedback learning
* **Auth**: Supabase as a user management/auth provider
* **External Services**: Plaid for banking, SendGrid for email, OpenAI API (optional, not required)
* **DevOps/Infra**: Docker Compose orchestrates everything; all secrets/config in `.env` or secure secret store

**Important**: If possible to do it simply, please stick to the previously determined technologies, softwares and tools. There is also just a single environment, don't call it anything different by adding suffixes or prefixes to the variables. All production and development systems are pointing the same thing. There will be no any other environment.

### **Service Responsibilities**

* **Frontend**: All UX; fetches from backend; real-time sync via WebSocket; handles offline/optimistic updates.
* **Backend**: REST/WS API; business logic; all DB ops; ML service integration.
* **ML Worker**: Handles transaction categorization; learns from user feedback; exposes prediction and feedback APIs.
* **Nginx**: Single public entrypoint; routes requests to appropriate service; rate-limits API/auth.
* **Postgres**: Source of truth for financial/accounting data.
* **Redis**: Message queue (Celery), real-time cache (WebSocket), ephemeral store for fast queries.

---

## **Domain Data Model (Objects & Relationships)**

**Core objects:**

* **User**: Profile, auth, locale, currency, theme, notification preferences
* **Account**: Checking, savings, credit, investment; current balance; Plaid connection; sync metadata
* **Transaction**: Linked to user/account/category; amount, description, merchant, dates, status, recurrence, ML suggestion
* **Category**: Hierarchical, custom or system; emoji/color/icon; used for classification
* **Budget**: Amount, category, period (monthly/weekly), alert thresholds, active state
* **Goal**: Name, description, type, target/current amounts, dates, milestones, auto-contribution, progress % and ETA

**Relationships:**

* One user → many accounts, transactions, categories, budgets, goals
* One account → many transactions
* One category → many transactions (can be hierarchical: parent/child)
* One goal → many contributions/milestones

**All IDs are UUID4.**
**All money values stored as integer cents.**
**All models have `created_at` and `updated_at` fields for auditability.**

**Important** : Database entries and relationships can be change, update the corresponding fields in the memory, whenever you changed them. But first always ask to user.

---

## **Business Logic and Services**

### **Core Functional Requirements**

* **Transaction CRUD** (with batch/bulk, CSV import, Plaid sync)
* **Automatic ML-based categorization** (with confidence score, explainable, user can correct/override, system learns from feedback)
* **Expense Receipt OCR** (image upload → text extraction → field mapping; user confirms values before saving)
* **Custom Rule Engine** (user-defined "if this, then that" categorization/auto-tag rules)
* **Budget and Goal Tracking** (progress, live alerts, celebratory milestones)
* **Real-time dashboard** (WebSocket push for new transactions, budgets, goals, sync status, notifications)
* **Comprehensive analytics** (spending trends, category breakdowns, monthly comparisons, insights)
* **Data import/export** (CSV, JSON)
* **Bank account integration** (Plaid sandbox support; future: multi-currency)

### **AI/ML System**

* **Model:** `all-MiniLM-L6-v2` via Sentence Transformers; ONNX-quantized for <10ms inference on CPU
* **Learning:** Few-shot—category "prototypes" updated by user-corrected examples
* **Confidence:** High (auto), medium (suggest), low (ask user)
* **Feedback loop:** Corrections update category prototype; weekly rebuild
* **Merchant/category mapping**: Auto-learns with every user-correction, merges fuzzy/regex rules
* **OCR**: pytesseract, then regex/heuristic field mapping (user reviews result)
* **Batch classification**: Supported for CSV imports and sync
* **Anomaly detection**: Simple ML (moving average, time series), flags outliers
* **A/B testing/monitoring**: Multi-model, performance tracked, rollbacks possible

### **API and Integration**

* All APIs are RESTful, versioned under `/api/`
* WebSocket endpoints for real-time events (`/ws`)
* All API responses typed with Pydantic; errors standardized; rate limiting for abusive patterns
* Secure JWT-based auth (via Supabase)
* All system decisions and suggestions auditable, explainable, and revertible by user

---

## **Frontend/User Experience**

**Design:**
Minimal, modern, privacy-respecting (blur mode), mobile-first, accessible, dark/light/auto modes.

**Key UI Patterns:**

* Real-time dashboard: Net worth, recent activity, insights, trends, budget alerts
* Transaction management: Table/list view, filter/search, edit/delete, CSV import/export, OCR upload
* Budget/goal planner: Visualize progress, set alerts, milestones, AI tips
* Settings: Profile, auth, theme, notifications, privacy, data export
* Error and loading states: Skeletons, toast/snackbar feedback, undo actions, friendly error boundaries

**Component Design:**

* Functional React components, Tailwind for style
* All state managed via Zustand (client) + React Query (server state)
* Real-time sync via WebSocket (with reconnect/optimistic patterns)
* Accessibility: ARIA, keyboard nav, screen reader support

---

## **DevOps/Deployment/Observability**

**Docker Compose** runs all services: frontend, backend, ML worker, Postgres, Redis, Nginx (public).

* **All secrets** from `.env` (never hardcode).
* **Production:** Nginx serves static frontend, proxies API/ws, terminates SSL, rate-limits API/auth.
* **Logging:** Structured, loglevel by env, performance tracked (process time header).
* **Healthchecks:** For all services; health endpoints for orchestration.
* **Database migrations:** Alembic, versioned, auto on deploy.
* **CI/CD:** All tests pass, code style checked, DB schema updated, blue-green deploys preferred.
* **Monitoring:** API response time, ML inference time, error rates, WebSocket uptime.

---

## **Security & Privacy**

* **All API endpoints authenticated** by default (JWT via Supabase)
* **No passwords stored**; all secrets encrypted at rest and in transit
* **All actions audited** (edit/delete logged by user/timestamp)
* **User data export/delete** flows (GDPR-friendly)
* **Rate limiting:** API (10r/s), Auth (5r/min), via Nginx
* **ML models**: No cloud AI unless explicitly enabled; local inference by default

---

## **Best Practices & Collaboration for LLM/AI Assistants**

* **Read this file and all referenced conventions before any code or architectural work.**
* **If a new feature is ambiguous, ask clarifying questions before implementing.**
* **Always explain any non-obvious system decision or API flow in your outputs.**
* **If an implementation detail is not in this file, prefer simplicity and explain your choice.**
* **For ML/AI: Default to CPU-friendly, explainable, local models. Only escalate to more complex/remote solutions if justified.**
* **If feedback, rules, or category mappings seem ambiguous, prompt the user for clarification.**
* **All model and field names should match those in the domain model unless there is a documented migration.**
* **For code examples or docs, use real types, clear comments for readability.**
* **Checkpoints:** Summarize all major changes in memory; update this file as necessary.

---

## **Key Non-Negotiable Conventions**

* All money stored as integer cents; always convert for display.
* All times stored in UTC, rendered in user's timezone.
* All major user actions (CRUD, sync, ML feedback) are auditable.
* No silent auto-categorization—always display ML confidence and allow override.
* Real-time events: Use WebSocket, not polling, for all dashboard/notification updates.
* All automated or AI-influenced flows must be explainable in plain English.
* *Undo* must be available for all destructive actions in the frontend.
* Data must be exportable by user at any time (GDPR, user autonomy).
* Production deploys must pass all tests and static analysis.
* For every system suggestion, allow user feedback to improve the system.

---

## **Sample "Memory" Summary for AI Assistant**

**Mission:**
Help build, improve, and document a modern, explainable, user-first finance tracker.
All features, decisions, and code must align with this project context and the data/business model described here.

**If any doubt exists, clarify, log your assumption, and record changes in memory.**
This file is living documentation: update it with all significant architectural, business, or model changes.

---

## **Development Guidance**

* **Model Definition Best Practices:**
    * Use model descriptions in the model files only, dont use schema to inherit from

* User wants to control entire running process with ./scripts/dev.sh for the start. Also user only using finance_tracker not finance_tracker_dev. 

* **Planning Before Implementation:**
    * Always analyze architectural implications before making changes
    * Consider effects on other files, imports, dependencies, and system components
    * Plan changes systematically to avoid cascading errors and ensure compatibility
    * Discuss design decisions and cross-dependencies before implementation
    * Use comprehensive planning phases for complex system modifications

---

## **Authentication System Architecture (Updated August 2025)**

### **Critical Authentication System Redesign**

**Problem Solved:** The authentication system suffered from response structure fragmentation causing 403 Forbidden errors, Plaid integration failures, and token refresh issues. Root cause was inconsistent response formats between different authentication flows (Supabase vs custom JWT, login vs refresh vs magic link).

### **Standardized Authentication Response Structure**

**All authentication endpoints now return consistent structure:**
```typescript
interface AuthResponse {
  user: User;              // Complete user object with all profile data
  accessToken: string;     // JWT access token (15-minute expiry)
  refreshToken: string;    // JWT refresh token (7-day expiry)
  expiresIn?: number;      // Token expiration in seconds
  tokenType?: string;      // "supabase" | "custom_jwt" for debugging
}
```

**Backend Implementation (`backend/app/schemas/auth.py`):**
- Created `StandardAuthResponse` Pydantic model for consistent typing
- Maintained backward compatibility with original `AuthResponse` for non-auth endpoints
- All auth service methods (`login_user`, `refresh_token`, `verify_magic_link_and_login`) return identical structure

**Frontend Implementation (`frontend/src/types/auth.ts`):**
- Updated `AuthResponse` interface with optional `expiresIn` and `tokenType` fields
- Ensures type safety across all authentication flows

### **Dual Authentication System Support**

**Backend handles both authentication types seamlessly:**

1. **Supabase Authentication:** Traditional email/password login
   - Uses Supabase session tokens
   - Backend fetches user data from Supabase and local database
   - Response marked with `tokenType: "supabase"`

2. **Custom JWT Authentication:** Magic link and development tokens
   - Uses our own JWT token generation (`app/utils/security.py`)
   - Direct database user lookup by token payload
   - Response marked with `tokenType: "custom_jwt"`

**Backend Dependencies (`backend/app/auth/dependencies.py`):**
- `get_current_user()` function handles both token types automatically
- Tries custom JWT verification first, falls back to Supabase
- Development mode supports `dev-mock-token-*` pattern for testing
- Maintains user session consistency across both auth types

### **Enhanced Frontend Token Management**

**Auth Store Improvements (`frontend/src/stores/authStore.ts`):**

1. **Response Validation:** All auth methods validate response structure before processing
2. **Consistent Token Storage:** Uses `apiClient.setAuthTokens(accessToken, refreshToken, expiresIn)`
3. **Magic Link Cookie Initialization:** `initializeFromCookies()` handles cookie-to-session transition
4. **Enhanced Error Handling:** Graceful degradation with proper error messages

**API Client Token Refresh (`frontend/src/services/api.ts`):**

1. **Robust Refresh Logic:** Validates JSON parsing and response structure
2. **Single Retry Pattern:** One-shot token refresh on 401 errors to prevent loops
3. **Enhanced Error Logging:** Detailed console output for debugging token issues
4. **Cookie + Header Support:** Supports both cookie-based and header-based authentication

### **Service Layer Error Handling**

**PlaidService Enhancements (`frontend/src/services/plaidService.ts`):**
- Handles both wrapped (`{success, data}`) and direct response formats
- Specific authentication error messages for better UX
- Graceful degradation when authentication fails

**BaseService Improvements (`frontend/src/services/base/BaseService.ts`):**
- Added response validation to prevent null/undefined propagation
- Enhanced error context with operation type, endpoint, and parameters
- Improved cache handling with validation

### **Development and Testing Infrastructure**

**AdminBypassButton (`frontend/src/components/ui/AdminBypassButton.tsx`):**
- Updated to use proper `AuthResponse` TypeScript interface
- Mock data matches actual backend user structure (camelCase fields)
- Consistent with new authentication response format

**Debug Tools (`debug-auth-flow.html`):**
- Comprehensive authentication flow testing
- Tests all critical endpoints: `/auth/me`, `/auth/refresh`, Plaid integration
- Visual pass/fail indicators for each authentication component
- Cookie management with proper expiration timing

**Development Token System:**
- `dev-mock-token-12345` works across all backend endpoints
- Consistent user ID `eadc6056-0799-423c-9bf9-6c1c4c811231` for testing
- Automatic user provisioning in development mode

### **Architecture Impact and Dependencies**

**Files Modified:**
1. **Backend:** `auth_service.py`, `auth.py` (schemas), `auth.py` (routes), `dependencies.py`
2. **Frontend:** `auth.ts` (types), `authStore.ts`, `api.ts`, `plaidService.ts`, `BaseService.ts`, `AdminBypassButton.tsx`
3. **Tools:** `debug-auth-flow.html`

**Key Design Decisions:**

1. **Additive Changes:** All modifications are backwards-compatible to prevent breaking existing functionality
2. **Unified Response Structure:** Single response format reduces complexity and bugs
3. **Enhanced Validation:** Multiple validation layers prevent undefined data propagation
4. **Dual Token Support:** Seamlessly handles both Supabase and custom JWT authentication
5. **Developer Experience:** Comprehensive testing tools and clear error messages

### **Authentication Flow Integration Points**

**Magic Link Flow:**
1. User registers → Backend sends magic link email
2. User clicks link → Backend sets HttpOnly cookies and redirects
3. Frontend `AuthInitializer` detects cookies → Calls `initializeFromCookies()`
4. Frontend fetches user data via `/auth/me` → Sets authentication state

**Token Refresh Flow:**
1. API request returns 401 → API client detects expired token
2. API client calls `/auth/refresh` with refresh token
3. Backend validates token → Returns new `AuthResponse` with user data
4. Frontend updates both tokens and user state seamlessly

**Service Integration:**
- All services (Plaid, Transactions, etc.) inherit authentication handling from BaseService
- Authentication failures gracefully handled with specific error messages
- No service-specific authentication logic required

### **Testing and Validation**

**Comprehensive Test Coverage:**
- Manual endpoint testing with curl commands
- Frontend integration testing with AdminBypassButton
- Debug tool comprehensive flow testing
- All authentication paths verified working

**Performance Characteristics:**
- Token refresh adds <100ms overhead on 401 errors
- Response validation adds minimal processing time
- Cookie initialization occurs only on app startup
- Development token bypass enables fast testing

This authentication system redesign resolves the core 403 Forbidden errors while establishing a robust, maintainable foundation for all authentication flows in the application.

---