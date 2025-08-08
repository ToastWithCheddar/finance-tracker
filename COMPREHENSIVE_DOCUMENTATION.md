# **Finance Tracker - Comprehensive Technical Documentation**

## **Table of Contents**

1. [Project Overview](#1-project-overview)
2. [Architecture Overview](#2-architecture-overview)
3. [Database Schema & Models](#3-database-schema--models)
4. [Backend Services & Business Logic](#4-backend-services--business-logic)
5. [API Routes & Endpoints](#5-api-routes--endpoints)
6. [Frontend Architecture](#6-frontend-architecture)
7. [State Management](#7-state-management)
8. [ML Worker & AI Services](#8-ml-worker--ai-services)
9. [Deployment & Infrastructure](#9-deployment--infrastructure)
10. [Development Workflow](#10-development-workflow)

---

## **1. Project Overview**

The Finance Tracker is a comprehensive personal finance management application designed to help users track income, expenses, set budgets, monitor financial goals, and gain AI-powered insights into their spending habits. The application follows modern microservices architecture with a focus on scalability, security, and user experience.

### **Key Features:**
- **Transaction Management**: Track income and expenses with automatic categorization
- **Budget Planning**: Set and monitor spending limits by category
- **Goal Setting**: Create and track financial goals with milestone notifications
- **AI-Powered Insights**: Machine learning-based transaction categorization and spending analysis
- **Real-time Updates**: WebSocket-based live transaction feeds and notifications
- **Multi-platform Support**: Responsive web interface with dark mode support
- **Bank Integration**: Plaid integration for automatic transaction syncing
- **Data Import/Export**: CSV import/export functionality
- **Advanced Analytics**: Spending trends, category breakdowns, and monthly comparisons

### **Tech Stack:**
- **Backend**: FastAPI (Python), SQLAlchemy ORM, PostgreSQL, Supabase Auth
- **Frontend**: React 18 + TypeScript, Zustand, React Query, Tailwind CSS
- **ML Services**: Python, Sentence Transformers, ONNX Runtime, Celery
- **Infrastructure**: Docker, Nginx, Redis, PostgreSQL
- **External Services**: Supabase (Authentication), Plaid (Banking)

---

## **2. Architecture Overview**

### **System Architecture Diagram**
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│                 │    │                 │    │                 │
│    Frontend     │◄──►│     Nginx       │◄──►│    Backend      │
│  (React/TS)     │    │  (Reverse       │    │   (FastAPI)     │
│                 │    │   Proxy)        │    │                 │
└─────────────────┘    └─────────────────┘    └─────┬───────────┘
                                                     │
                       ┌─────────────────┐          │
                       │                 │          │
                       │   PostgreSQL    │◄─────────┤
                       │   (Database)    │          │
                       │                 │          │
                       └─────────────────┘          │
                                                     │
┌─────────────────┐    ┌─────────────────┐          │
│                 │    │                 │          │
│   ML Worker     │◄──►│     Redis       │◄─────────┤
│   (Python)      │    │   (Message      │          │
│                 │    │    Queue)       │          │
└─────────────────┘    └─────────────────┘          │
                                                     │
                       ┌─────────────────┐          │
                       │                 │          │
                       │   Supabase      │◄─────────┘
                       │ (Auth Service)  │
                       │                 │
                       └─────────────────┘
```

### **Component Responsibilities:**

1. **Frontend (React/TypeScript)**: User interface, state management, API consumption
2. **Backend (FastAPI)**: Business logic, API endpoints, database operations, authentication
3. **ML Worker**: Machine learning inference, transaction categorization, model training
4. **PostgreSQL**: Primary data storage for all financial data
5. **Redis**: Message queue for ML tasks, caching, real-time data
6. **Nginx**: Reverse proxy, load balancing, static file serving, SSL termination
7. **Supabase**: External authentication service, user management

---

## **3. Database Schema & Models**

### **Core Models Overview**

The application uses SQLAlchemy ORM with a comprehensive relational schema designed for financial data integrity and performance.

#### **BaseModel (`backend/app/models/base.py`)**
```python
class BaseModel(Base):
    __abstract__ = True
    
    id: UUID = Primary key (UUID4)
    created_at: DateTime = Server timestamp
    updated_at: DateTime = Auto-updated timestamp
```
All models inherit from BaseModel, providing consistent ID generation and audit timestamps.

#### **User Model (`backend/app/models/user.py`)**
```python
class User(BaseModel):
    __tablename__ = "users"
    
    # Authentication & Identity
    supabase_user_id: UUID = Unique link to Supabase auth
    email: str = Unique, indexed
    first_name: Optional[str]
    last_name: Optional[str]
    display_name: Optional[str]
    avatar_url: Optional[str]
    
    # Localization
    locale: str = Default "en-US"
    timezone: str = Default "UTC"
    currency: str = Default "USD"
    
    # Account Status
    is_active: bool = Default True
    is_verified: bool = Default False
    
    # Preferences
    notification_email: bool = Default True
    notification_push: bool = Default True
    theme: str = Default "light"
```

**Relationships:**
- One-to-many: accounts, transactions, budgets, goals, insights, categories
- One-to-one: preferences

#### **Account Model (`backend/app/models/account.py`)**
```python
class Account(BaseModel):
    __tablename__ = "accounts"
    
    user_id: UUID = Foreign key to users
    name: str = Account display name
    account_type: str = checking, savings, credit_card, investment
    balance_cents: BigInteger = Balance in smallest currency unit
    currency: str = Default "USD"
    is_active: bool = Default True
    
    # Plaid Integration
    plaid_account_id: Optional[str] = Unique Plaid identifier
    plaid_access_token: Optional[str] = Encrypted access token
    plaid_item_id: Optional[str] = Plaid item identifier
    last_sync_at: Optional[DateTime] = Last synchronization timestamp
    
    # Sync Status & Health
    account_metadata: Optional[JSONB] = Flexible metadata storage
    sync_status: str = manual, syncing, synced, error, disconnected
    last_sync_error: Optional[str] = Error message from last sync
    connection_health: str = healthy, warning, failed, not_connected
    sync_frequency: str = daily, weekly, monthly, manual
```

**Properties:**
- `balance_dollars`: Converts cents to dollars
- `is_plaid_connected`: Checks Plaid connection status
- `needs_sync`: Determines if sync is needed (>24 hours old)

#### **Transaction Model (`backend/app/models/transaction.py`)**
```python
class Transaction(BaseModel):
    __tablename__ = "transactions"
    
    # Core Transaction Data
    user_id: UUID = Foreign key to users
    account_id: UUID = Foreign key to accounts
    category_id: Optional[UUID] = Foreign key to categories
    
    # Financial Details
    amount_cents: BigInteger = Amount in smallest currency unit
    currency: str = Default "USD"
    description: str = Transaction description
    merchant: Optional[str] = Merchant name
    merchant_logo: Optional[str] = Merchant logo URL
    
    # Dates
    transaction_date: Date = Actual transaction date
    authorized_date: Optional[Date] = Authorization date
    posted_date: Optional[Date] = Posted date
    
    # Status & Classification
    status: str = pending, posted, cancelled
    is_recurring: bool = Subscription/recurring payment flag
    is_transfer: bool = Account transfer flag
    is_hidden: bool = User visibility flag
    
    # Recurring Transaction Support
    recurring_rule: Optional[JSONB] = Cron-like recurrence rules
    recurring_parent_id: Optional[UUID] = Parent recurring transaction
    
    # Geographic & Additional Data
    location: Optional[JSONB] = {lat, lng, address, city, state, country}
    notes: Optional[str] = User notes
    tags: Optional[List[str]] = User-defined tags
    
    # External Integration
    plaid_transaction_id: Optional[str] = Unique Plaid identifier
    plaid_category: Optional[List[str]] = Plaid-provided categories
    
    # ML/AI Enhancement
    confidence_score: Optional[float] = ML categorization confidence
    ml_suggested_category_id: Optional[UUID] = ML-suggested category
    metadata_json: Optional[JSONB] = Flexible metadata storage
```

**Indexes:**
- `idx_transaction_user_date`: (user_id, transaction_date)
- `idx_transaction_account_date`: (account_id, transaction_date)
- `idx_transaction_category`: (category_id)
- `idx_transaction_merchant`: (merchant)
- `idx_transaction_amount`: (amount_cents)
- `idx_transaction_status`: (status)
- `idx_transaction_plaid_id`: (plaid_transaction_id)
- `idx_transaction_recurring`: (is_recurring)

#### **Category Model (`backend/app/models/category.py`)**
```python
class Category(BaseModel):
    __tablename__ = "categories"
    
    # Ownership & Identity
    user_id: Optional[UUID] = Foreign key to users (NULL for system categories)
    name: str = Category name
    description: Optional[str] = Category description
    
    # Visual Representation
    emoji: Optional[str] = Category emoji
    color: Optional[str] = Hex color code
    icon: Optional[str] = Icon identifier
    
    # Hierarchical Structure
    parent_id: Optional[UUID] = Parent category for subcategories
    
    # System vs Custom
    is_system: bool = System-defined category flag
    is_active: bool = Active status flag
    
    # Ordering
    sort_order: int = Display order
```

**Constraints:**
- Unique constraint: (user_id, name)
- Indexes on user_id+name, is_system, parent_id

#### **Budget Model (`backend/app/models/budget.py`)**
```python
class Budget(BaseModel):
    __tablename__ = "budgets"
    
    user_id: UUID = Foreign key to users
    category_id: Optional[UUID] = Foreign key to categories
    name: str = Budget name
    amount_cents: BigInteger = Budget amount in cents
    period: str = monthly, weekly, yearly
    start_date: Date = Budget start date
    end_date: Optional[Date] = Budget end date
    alert_threshold: float = Alert percentage (default 0.8)
    is_active: bool = Active status
```

#### **Goal Model (`backend/app/models/goal.py`)**
```python
class Goal(BaseModel):
    __tablename__ = "goals"
    
    # Basic Goal Information
    user_id: UUID = Foreign key to users
    name: str = Goal name
    description: Optional[str] = Goal description
    target_amount_cents: BigInteger = Target amount in cents
    current_amount_cents: BigInteger = Current progress in cents
    
    # Goal Classification
    goal_type: GoalType = savings, debt_payoff, emergency_fund, investment, purchase, other
    priority: GoalPriority = low, medium, high, critical
    status: GoalStatus = active, completed, paused, cancelled
    
    # Timeline
    start_date: Optional[Date] = Goal start date
    target_date: Optional[Date] = Target completion date
    completed_date: Optional[Date] = Actual completion date
    
    # Auto-contribution Settings
    auto_contribute: bool = Automatic contribution flag
    auto_contribution_amount: Optional[BigInteger] = Auto-contribution amount
    auto_contribution_source: Optional[str] = Source account
    
    # Progress Tracking
    last_contribution_date: Optional[Date] = Last contribution date
    contribution_frequency: ContributionFrequency = daily, weekly, monthly, quarterly, yearly
    monthly_target_cents: Optional[BigInteger] = Monthly target amount
    celebration_message: Optional[str] = Completion message
    
    # Milestone Configuration
    milestone_percent: int = Milestone percentage (default 25%)
    last_milestone: Optional[int] = Last reached milestone
```

**Properties:**
- `progress_percentage`: Calculated progress percentage
- `remaining`: Remaining amount to reach goal
- `is_achieved`: Goal completion status
- `days_remaining`: Days until target date

#### **Supporting Models**

**GoalContribution** - Individual contributions to goals
**GoalMilestone** - Milestone achievement tracking
**UserPreferences** - User-specific settings and preferences
**Insight** - AI-generated financial insights
**MLModelPerformance** - ML model performance tracking

### **Database Relationships Summary**

```
User (1) ──── (M) Account
User (1) ──── (M) Transaction
User (1) ──── (M) Category
User (1) ──── (M) Budget
User (1) ──── (M) Goal
User (1) ──── (1) UserPreferences

Account (1) ──── (M) Transaction
Category (1) ──── (M) Transaction
Category (1) ──── (M) Budget

Goal (1) ──── (M) GoalContribution
Goal (1) ──── (M) GoalMilestone

Transaction (1) ──── (M) GoalContribution
```

---

## **4. Backend Services & Business Logic**

### **Service Architecture**

The backend follows a layered service architecture with clear separation of concerns:

1. **Base Service Layer**: Common CRUD operations
2. **Domain Services**: Business logic for specific domains
3. **Integration Services**: External service integrations
4. **Utility Services**: Cross-cutting concerns

#### **BaseService (`backend/app/services/base_service.py`)**

Generic service class providing common CRUD operations:

```python
class BaseService(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType])
    
    # Core CRUD Operations
    def get(db: Session, id: Any) -> Optional[ModelType]
    def get_multi(db: Session, skip: int, limit: int, user_id: UUID, filters: Dict) -> List[ModelType]
    def create(db: Session, obj_in: CreateSchemaType, user_id: UUID) -> ModelType
    def update(db: Session, db_obj: ModelType, obj_in: UpdateSchemaType) -> ModelType
    def delete(db: Session, id: Any) -> Optional[ModelType]
    
    # Utility Methods
    def count(db: Session, user_id: UUID) -> int
    def exists(db: Session, id: Any) -> bool
```

**Features:**
- Generic type support for type safety
- Automatic user_id filtering for multi-tenant data
- Flexible filtering system
- Pagination support

#### **UserService (`backend/app/services/user_service.py`)**

Manages user accounts and profiles:

```python
class UserService(BaseService[User, UserCreate, UserUpdate]):
    # Authentication & Identity
    def get_by_email(db: Session, email: str) -> Optional[User]
    def get_by_supabase_id(db: Session, supabase_user_id: UUID) -> Optional[User]
    
    # User Management
    def create_user(db: Session, user_create: UserCreate) -> User
    def update_user(db: Session, user_id: UUID, user_update: UserUpdate) -> Optional[User]
    def deactivate_user(db: Session, user_id: UUID) -> Optional[User]
    def verify_user_email(db: Session, user_id: UUID) -> Optional[User]
    
    # Search & Discovery
    def get_active_users(db: Session, skip: int, limit: int) -> List[User]
    def search_users(db: Session, query: str, skip: int, limit: int) -> List[User]
```

#### **CategoryService (`backend/app/services/category_service.py`)**

Manages transaction categories with hierarchical support:

```python
class CategoryService(BaseService[Category, CategoryCreate, CategoryUpdate]):
    # Category Retrieval
    def get_categories(db: Session, user_id: UUID, include_system: bool, 
                      parent_only: bool, search: str) -> List[Category]
    def get_system_categories(db: Session) -> List[Category]
    def get_user_categories(db: Session, user_id: UUID, include_system: bool) -> List[Category]
    
    # Category Management
    def get_by_name(db: Session, name: str, user_id: UUID) -> Optional[Category]
    def create_user_category(db: Session, category_create: CategoryCreate, user_id: UUID) -> Category
    def get_category_hierarchy(db: Session, user_id: UUID) -> List[Category]
    
    # Analytics
    def get_category_usage_stats(db: Session, user_id: UUID) -> Dict[str, Any]
```

**Features:**
- System vs user categories
- Hierarchical category structure
- Search and filtering capabilities
- Usage statistics and analytics

#### **TransactionService (`backend/app/services/transaction_service.py`)**

Core transaction management with ML integration:

```python
class TransactionService:
    # Transaction CRUD
    @staticmethod
    def create_transaction(db: Session, transaction: TransactionCreate, user_id: int) -> Transaction
    def get_transaction(db: Session, transaction_id: int, user_id: int) -> Optional[Transaction]
    def update_transaction(db: Session, transaction: Transaction, update: TransactionUpdate) -> Transaction
    def delete_transaction(db: Session, transaction: Transaction) -> bool
    
    # Advanced Querying
    def get_transactions_with_filters(db: Session, user_id: int, 
                                    filters: TransactionFilter, 
                                    pagination: TransactionPagination) -> Tuple[List[Transaction], int]
    
    # Bulk Operations
    def import_transactions_from_csv(db: Session, user_id: int, 
                                   transactions: List[TransactionCreate]) -> List[Transaction]
    def batch_update_transactions(db: Session, updates: List[TransactionUpdate]) -> List[Transaction]
    
    # Analytics
    def get_spending_by_category(db: Session, user_id: int, date_range: DateRange) -> Dict[str, float]
    def get_monthly_trends(db: Session, user_id: int) -> List[Dict[str, Any]]
    def calculate_transaction_insights(db: Session, user_id: int) -> Dict[str, Any]
```

**ML Integration:**
The service integrates with the ML worker for automatic categorization:
- Calls ML service for category prediction
- Handles confidence thresholds
- Provides fallback mechanisms
- Manages ML suggestion storage

#### **BudgetService (`backend/app/services/budget_service.py`)**

Budget management and tracking:

```python
class BudgetService:
    # Budget CRUD
    def create_budget(db: Session, budget_create: BudgetCreate, user_id: UUID) -> Budget
    def get_budget(db: Session, budget_id: UUID, user_id: UUID) -> Optional[Budget]
    def get_budgets(db: Session, user_id: UUID, filters: BudgetFilter) -> List[Budget]
    def update_budget(db: Session, budget: Budget, budget_update: BudgetUpdate) -> Budget
    def delete_budget(db: Session, budget: Budget) -> bool
    
    # Budget Analysis
    def calculate_budget_usage(db: Session, budget: Budget, current_date: date) -> BudgetUsage
    def get_budget_summary(db: Session, user_id: UUID, period: BudgetPeriod) -> BudgetSummary
    def check_budget_alerts(db: Session, user_id: UUID) -> List[BudgetAlert]
    
    # Budget Intelligence
    def suggest_budget_amounts(db: Session, user_id: UUID) -> Dict[str, float]
    def analyze_budget_performance(db: Session, user_id: UUID) -> Dict[str, Any]
```

**Features:**
- Period-based budgeting (monthly, weekly, yearly)
- Real-time usage tracking
- Alert system with configurable thresholds
- Budget performance analytics
- AI-powered budget suggestions

#### **GoalService (`backend/app/services/goal_service.py`)**

Financial goal management and tracking:

```python
class GoalService:
    # Goal Management
    def create_goal(db: Session, user_id: UUID, goal_data: GoalCreate) -> Goal
    def get_goals(db: Session, user_id: UUID, status: GoalStatus, 
                 goal_type: GoalType, priority: GoalPriority) -> Dict[str, Any]
    def get_goal(db: Session, user_id: UUID, goal_id: UUID) -> Optional[Goal]
    def update_goal(db: Session, user_id: UUID, goal_id: UUID, goal_data: GoalUpdate) -> Optional[Goal]
    def delete_goal(db: Session, user_id: UUID, goal_id: UUID) -> bool
    
    # Contribution Management
    def add_contribution(db: Session, user_id: UUID, goal_id: UUID, 
                        contribution: GoalContributionCreate) -> GoalContribution
    def get_contributions(db: Session, goal_id: UUID) -> List[GoalContribution]
    
    # Progress Tracking
    def update_goal_progress(db: Session, goal: Goal, amount: float) -> Goal
    def check_milestones(db: Session, goal: Goal) -> List[MilestoneAlert]
    def calculate_goal_projection(db: Session, goal: Goal) -> Dict[str, Any]
    
    # Analytics
    def get_goal_insights(db: Session, user_id: UUID) -> Dict[str, Any]
    def generate_progress_report(db: Session, user_id: UUID) -> Dict[str, Any]
```

**Features:**
- Multiple goal types (savings, debt payoff, emergency fund, etc.)
- Automatic contribution tracking
- Milestone notifications
- Progress projections
- Real-time WebSocket updates

### **Integration Services**

#### **Enhanced Plaid Service**
- Bank account connection and management
- Transaction synchronization
- Account balance monitoring
- Connection health tracking
- Automatic reconciliation

#### **Transaction Sync Service**
- Scheduled transaction imports
- Duplicate detection and prevention
- Conflict resolution
- Sync status monitoring

#### **Account Insights Service**
- Spending pattern analysis
- Anomaly detection
- Cashflow predictions
- Account health scoring

---

## **5. API Routes & Endpoints**

### **API Structure Overview**

The FastAPI backend provides a comprehensive REST API with the following route groups:

```
/api/
├── auth/           # Authentication endpoints
├── users/          # User management
├── accounts/       # Account management
├── transactions/   # Transaction CRUD and analytics
├── categories/     # Category management
├── budgets/        # Budget management
├── goals/          # Goal management
├── ml/             # ML service endpoints
├── health/         # Health checks
└── ws/             # WebSocket endpoints
```

#### **Authentication Routes (`/api/auth/`)**

**User Registration & Login:**
```python
POST /api/auth/register
    Request: UserRegister (email, password, first_name, last_name)
    Response: AuthResponse (user, access_token, refresh_token)

POST /api/auth/login
    Request: UserLogin (email, password)
    Response: AuthResponse (user, access_token, refresh_token)

POST /api/auth/logout
    Headers: Authorization: Bearer <token>
    Response: 204 No Content

POST /api/auth/refresh
    Request: RefreshTokenRequest (refresh_token)
    Response: AuthResponse (user, access_token, refresh_token)
```

**Password Management:**
```python
POST /api/auth/request-password-reset
    Request: PasswordResetRequest (email)
    Response: 204 No Content

POST /api/auth/reset-password
    Request: PasswordResetConfirm (token, new_password)
    Response: AuthResponse
```

**Email Verification:**
```python
POST /api/auth/verify-email
    Request: EmailVerification (token, email)
    Response: AuthResponse (success, message)

POST /api/auth/resend-verification
    Request: ResendVerificationRequest (email)
    Response: 204 No Content
```

**Authentication Dependencies:**
- `get_current_user`: Validates JWT token and returns user
- `get_current_active_user`: Ensures user is active
- `require_auth`: Basic authentication requirement

#### **User Routes (`/api/users/`)**

```python
GET /api/users/me
    Response: UserResponse (current user profile)

PUT /api/users/me
    Request: UserUpdate (profile updates)
    Response: UserResponse (updated profile)

DELETE /api/users/me
    Response: {"message": "Account deactivated successfully"}

GET /api/users/search?query={query}&skip={skip}&limit={limit}
    Response: List[UserProfile] (search results)

# User Preferences
GET /api/users/me/preferences
    Response: UserPreferencesResponse

PUT /api/users/me/preferences
    Request: UserPreferencesUpdate
    Response: UserPreferencesResponse
```

#### **Transaction Routes (`/api/transactions/`)**

**Basic CRUD:**
```python
POST /api/transactions/
    Request: TransactionCreate
    Response: TransactionResponse
    Features: Auto-categorization via ML, real-time notifications

GET /api/transactions/{transaction_id}
    Response: TransactionResponse

PUT /api/transactions/{transaction_id}
    Request: TransactionUpdate
    Response: TransactionResponse

DELETE /api/transactions/{transaction_id}
    Response: 204 No Content
```

**Advanced Querying:**
```python
GET /api/transactions/
    Query Parameters:
        - start_date, end_date: Date range filter
        - category: Category filter
        - transaction_type: Type filter
        - min_amount, max_amount: Amount range
        - search_query: Text search
        - page, per_page: Pagination
    Response: PaginatedResponse[TransactionResponse]

GET /api/transactions/search
    Query: Advanced search with multiple filters
    Response: TransactionSearchResponse
```

**Bulk Operations:**
```python
POST /api/transactions/import/csv
    Request: Multipart form with CSV file
    Response: BulkImportResponse (imported_count, errors)

POST /api/transactions/bulk-update
    Request: List[TransactionUpdate]
    Response: List[TransactionResponse]

POST /api/transactions/bulk-categorize
    Request: BulkCategorizeRequest (transaction_ids, category_id)
    Response: BulkOperationResponse
```

**Analytics:**
```python
GET /api/transactions/analytics/spending-by-category
    Query: date_range, category_ids
    Response: SpendingByCategoryResponse

GET /api/transactions/analytics/monthly-trends
    Query: months_back, include_projections
    Response: MonthlyTrendsResponse

GET /api/transactions/analytics/insights
    Response: TransactionInsightsResponse
```

#### **Category Routes (`/api/categories/`)**

```python
GET /api/categories/
    Query: include_system, parent_only, search
    Response: List[CategoryResponse]

POST /api/categories/
    Request: CategoryCreate
    Response: CategoryResponse

PUT /api/categories/{category_id}
    Request: CategoryUpdate
    Response: CategoryResponse

DELETE /api/categories/{category_id}
    Response: 204 No Content

GET /api/categories/hierarchy
    Response: CategoryHierarchyResponse (nested structure)

GET /api/categories/usage-stats
    Response: CategoryUsageStatsResponse
```

#### **Budget Routes (`/api/budgets/`)**

```python
GET /api/budgets/
    Query: category_id, period, is_active, date_range
    Response: List[BudgetResponse]

POST /api/budgets/
    Request: BudgetCreate
    Response: BudgetResponse

PUT /api/budgets/{budget_id}
    Request: BudgetUpdate
    Response: BudgetResponse

DELETE /api/budgets/{budget_id}
    Response: 204 No Content

GET /api/budgets/{budget_id}/usage
    Response: BudgetUsageResponse (spent, remaining, percentage)

GET /api/budgets/summary
    Query: period (current_month, current_year, etc.)
    Response: BudgetSummaryResponse

GET /api/budgets/alerts
    Response: List[BudgetAlert] (over-budget warnings)
```

#### **Goal Routes (`/api/goals/`)**

```python
GET /api/goals/
    Query: status, goal_type, priority
    Response: GoalListResponse (goals, stats)

POST /api/goals/
    Request: GoalCreate
    Response: GoalResponse

GET /api/goals/{goal_id}
    Response: GoalResponse (with contributions and milestones)

PUT /api/goals/{goal_id}
    Request: GoalUpdate
    Response: GoalResponse

DELETE /api/goals/{goal_id}
    Response: 204 No Content

POST /api/goals/{goal_id}/contributions
    Request: GoalContributionCreate
    Response: GoalContributionResponse

GET /api/goals/{goal_id}/contributions
    Response: List[GoalContributionResponse]

GET /api/goals/insights
    Response: GoalInsightsResponse (progress analysis, recommendations)
```

#### **ML Service Routes (`/api/ml/`)**

```python
POST /api/ml/categorize
    Request: MLCategorizeRequest (description, amount, merchant)
    Response: MLCategorizeResponse (predicted_category, confidence)

POST /api/ml/feedback
    Request: MLFeedbackRequest (transaction_id, predicted_category, actual_category)
    Response: MLFeedbackResponse

GET /api/ml/model-performance
    Response: MLModelPerformanceResponse (accuracy, precision, recall)

POST /api/ml/retrain
    Request: MLRetrainRequest (user_id, include_global_data)
    Response: MLRetrainResponse (status, new_accuracy)
```

#### **WebSocket Endpoints (`/ws/`)**

```python
WS /ws/connect
    Authentication: JWT token in query parameter
    Messages:
        - transaction_created: New transaction notification
        - transaction_updated: Transaction update notification
        - budget_alert: Budget threshold exceeded
        - goal_milestone: Goal milestone reached
        - account_sync: Account synchronization status
```

### **API Features**

#### **Authentication & Security**
- JWT-based authentication with refresh tokens
- Supabase integration for user management
- Rate limiting (10 requests/second for API, 5 requests/minute for auth)
- CORS configuration for frontend integration
- Request validation with Pydantic schemas

#### **Error Handling**
- Consistent error response format
- HTTP status code standards
- Detailed error messages for development
- Sanitized error messages for production

#### **Pagination**
- Cursor-based pagination for large datasets
- Configurable page sizes
- Total count information
- Navigation links

#### **Filtering & Search**
- Multi-field filtering capabilities
- Full-text search on descriptions
- Date range filtering
- Amount range filtering
- Category and type filtering

#### **Performance Optimizations**
- Database query optimization with indexes
- Lazy loading for relationships
- Caching for frequently accessed data
- Async/await for I/O operations

---

## **6. Frontend Architecture**

### **React Application Structure**

The frontend is built with React 18 and TypeScript, following modern patterns and best practices:

```
frontend/src/
├── components/          # Reusable UI components
│   ├── ui/             # Basic UI primitives
│   ├── auth/           # Authentication components
│   ├── dashboard/      # Dashboard-specific components
│   ├── transactions/   # Transaction management
│   ├── budgets/        # Budget components
│   ├── goals/          # Goal components
│   ├── categories/     # Category management
│   ├── accounts/       # Account components
│   ├── layout/         # Layout components
│   └── common/         # Common utilities
├── pages/              # Top-level page components
├── hooks/              # Custom React hooks
├── services/           # API clients and external services
├── stores/             # State management (Zustand)
├── types/              # TypeScript type definitions
├── utils/              # Utility functions
└── assets/             # Static assets
```

#### **Component Architecture**

**UI Component Library (`src/components/ui/`)**

Built with Tailwind CSS and following atomic design principles:

```typescript
// Basic Components
export const Button: React.FC<ButtonProps>
export const Input: React.FC<InputProps>
export const Card: React.FC<CardProps>
export const Modal: React.FC<ModalProps>
export const LoadingSpinner: React.FC<SpinnerProps>
export const Toast: React.FC<ToastProps>

// Complex Components
export const ThemeToggle: React.FC // Dark mode toggle with system preference
export const DevModeIndicator: React.FC // Development mode indicator
export const AdminBypassButton: React.FC // Development bypass for auth
```

**Features:**
- Dark mode support with Tailwind's `dark:` classes
- Accessible components following ARIA guidelines
- Responsive design with mobile-first approach
- Consistent styling with design system

**Layout Components (`src/components/layout/`)**

```typescript
// Navigation.tsx
export function Navigation({ className }: NavigationProps): JSX.Element
export function Layout({ children, showNavigation }: LayoutProps): JSX.Element
```

**Navigation Features:**
- Responsive navigation with mobile-friendly design
- Active route highlighting
- User profile display with displayName fallback
- Theme toggle integration
- Logout functionality

**Dashboard Components (`src/components/dashboard/`)**

```typescript
// Analytics Visualizations
export const CategoryPieChart: React.FC<CategoryPieChartProps>
export const SpendingTrendsChart: React.FC<SpendingTrendsProps>
export const MonthlyComparisonChart: React.FC<MonthlyComparisonProps>

// Interactive Components
export const DashboardFilters: React.FC<DashboardFiltersProps>
export const RealtimeTransactionFeed: React.FC<RealtimeTransactionFeedProps>
export const NotificationPanel: React.FC<NotificationPanelProps>
```

**Chart Features:**
- Recharts integration for data visualization
- Responsive charts that adapt to container size
- Interactive tooltips and legends
- Color-coded categories with consistent theming
- Real-time data updates

#### **Page Components (`src/pages/`)**

**Dashboard Page (`Dashboard.tsx`)**
```typescript
export function Dashboard(): JSX.Element
```

**Features:**
- Real-time financial overview with key metrics
- Interactive date range filtering
- Dynamic chart updates based on filters
- Quick action buttons for common tasks
- Recent transaction feed
- Getting started guide for new users
- Error boundaries and loading states

**Transaction Page (`Transactions.tsx`)**
- Complete transaction management interface
- Advanced filtering and search capabilities
- Bulk operations support
- CSV import/export functionality
- ML category suggestions with confidence indicators
- Real-time updates via WebSocket

**Settings Page (`Settings.tsx`)**
- User profile management
- Comprehensive user preferences
- Theme selection (light/dark/auto)
- Notification settings
- Privacy controls
- Account management

### **Routing & Navigation**

**App.tsx - Route Configuration:**
```typescript
function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <ToastProvider>
          <Router>
            <Routes>
              <Route path="/login" element={<Login />} />
              
              {/* Protected Routes */}
              <Route path="/dashboard" element={
                <ProtectedRoute>
                  <Layout><Dashboard /></Layout>
                </ProtectedRoute>
              } />
              
              {/* Other protected routes... */}
              
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="*" element={<Navigate to="/dashboard" replace />} />
            </Routes>
          </Router>
        </ToastProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}
```

**ProtectedRoute Component:**
- JWT token validation
- Automatic token refresh
- Redirect to login for unauthenticated users
- Loading states during authentication checks

### **Custom Hooks**

#### **Data Fetching Hooks (`src/hooks/`)**

```typescript
// Dashboard Analytics
export const useDashboardAnalytics = (filters: DashboardFilters) => {
  return useQuery({
    queryKey: ['dashboard', 'analytics', filters],
    queryFn: () => dashboardService.getAnalytics(filters),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

// Transaction Management
export const useTransactions = (filters: TransactionFilter) => {
  return useQuery({
    queryKey: ['transactions', filters],
    queryFn: () => transactionService.getTransactions(filters),
    keepPreviousData: true,
  });
};

// Real-time WebSocket Hook
export const useWebSocket = () => {
  const { user } = useAuthStore();
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected');
  
  // WebSocket connection management
  // Message handling and dispatch
  // Automatic reconnection logic
};
```

**Features:**
- React Query integration for server state
- Optimistic updates for better UX
- Error handling and retry logic
- Caching and background updates
- Real-time data synchronization

### **Error Handling & Loading States**

**Error Boundary (`src/components/common/ErrorBoundary.tsx`)**
```typescript
export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  // Catches JavaScript errors anywhere in the child component tree
  // Logs error information
  // Displays fallback UI
  // Provides error reporting capabilities
}
```

**Async Error Boundary**
- Handles async errors from React Query
- Network error recovery
- User-friendly error messages
- Retry mechanisms

**Loading States**
- Skeleton screens for initial loading
- Progressive loading for large datasets
- Optimistic updates for immediate feedback
- Loading indicators with proper accessibility

---

## **7. State Management**

### **Zustand Store Architecture**

The application uses Zustand for client-side state management, providing a lightweight and TypeScript-friendly solution.

#### **Authentication Store (`src/stores/authStore.ts`)**

```typescript
interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

interface AuthActions {
  login: (credentials: LoginCredentials) => Promise<void>;
  register: (credentials: RegisterCredentials) => Promise<void>;
  logout: () => void;
  refreshToken: () => Promise<void>;
  updateUser: (user: Partial<User>) => void;
  clearError: () => void;
  checkTokenExpiration: () => Promise<void>;
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      // State initialization
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      // Authentication actions
      login: async (credentials) => {
        // JWT token handling
        // Secure token storage
        // User state updates
      },

      logout: () => {
        // Token cleanup
        // State reset
        // Navigation handling
      },

      refreshToken: async () => {
        // Automatic token refresh
        // Error handling for expired refresh tokens
      },
    }),
    {
      name: 'auth-store',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
```

**Features:**
- Persistent authentication state
- Automatic token refresh
- Secure token storage with encryption
- Error handling and recovery
- Type-safe state updates

**Selector Hooks:**
```typescript
export const useAuthUser = () => useAuthStore((state) => state.user);
export const useIsAuthenticated = () => useAuthStore((state) => state.isAuthenticated);
export const useAuthLoading = () => useAuthStore((state) => state.isLoading);
export const useAuthError = () => useAuthStore((state) => state.error);
```

#### **Theme Store (`src/stores/themeStore.ts`)**

```typescript
export type Theme = 'light' | 'dark' | 'auto';

interface ThemeState {
  theme: Theme;
  systemTheme: 'light' | 'dark';
  actualTheme: 'light' | 'dark';
  
  setTheme: (theme: Theme) => void;
  initializeTheme: () => void;
  applyTheme: () => void;
}

export const useThemeStore = create<ThemeState>()(
  subscribeWithSelector((set, get) => ({
    theme: 'auto',
    systemTheme: 'light',
    actualTheme: 'light',

    setTheme: (theme: Theme) => {
      // Theme resolution (auto -> system preference)
      // DOM class manipulation for Tailwind
      // localStorage persistence
      // Meta theme-color updates for mobile
    },

    initializeTheme: () => {
      // System theme detection
      // Stored preference retrieval
      // Initial theme application
    },
  }))
);
```

**Advanced Features:**
- Automatic system theme detection
- Smooth theme transitions
- Mobile meta theme-color updates
- Persistent user preferences
- Real-time system theme change detection

**Theme Integration:**
```typescript
// System theme change listener
if (typeof window !== 'undefined') {
  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
  
  const handleSystemThemeChange = (e: MediaQueryListEvent) => {
    const systemTheme = e.matches ? 'dark' : 'light';
    // Update store state
    // Apply theme if using auto mode
  };
  
  mediaQuery.addEventListener('change', handleSystemThemeChange);
}
```

#### **Realtime Store (`src/stores/realtimeStore.ts`)**

```typescript
interface RealtimeState {
  // WebSocket connection state
  isConnected: boolean;
  connectionStatus: 'connecting' | 'connected' | 'disconnected' | 'error';
  
  // Real-time data
  recentTransactions: Transaction[];
  notifications: Notification[];
  liveUpdates: Record<string, any>;
  
  // Actions
  connect: () => void;
  disconnect: () => void;
  addTransaction: (transaction: Transaction) => void;
  updateTransaction: (transaction: Transaction) => void;
  addNotification: (notification: Notification) => void;
  markNotificationRead: (id: string) => void;
}
```

**WebSocket Integration:**
- Automatic connection management
- Message routing and handling
- Optimistic updates
- Error recovery and reconnection
- Real-time notification system

### **Server State Management (React Query)**

#### **Query Client Configuration (`src/services/queryClient.ts`)**

```typescript
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      cacheTime: 10 * 60 * 1000, // 10 minutes
      retry: (failureCount, error) => {
        // Custom retry logic based on error type
      },
      refetchOnWindowFocus: false,
      refetchOnMount: true,
    },
    mutations: {
      retry: 1,
      onError: (error) => {
        // Global error handling
      },
    },
  },
});
```

#### **Custom Query Hooks**

**Dashboard Hooks (`src/hooks/useDashboard.ts`)**
```typescript
export const useDashboardAnalytics = (filters: DashboardFilters) => {
  return useQuery({
    queryKey: ['dashboard', 'analytics', filters],
    queryFn: () => dashboardService.getAnalytics(filters),
    enabled: !!filters.start_date && !!filters.end_date,
    staleTime: 2 * 60 * 1000, // 2 minutes for fresh data
  });
};

export const useSpendingTrends = (period: 'monthly' | 'weekly' | 'yearly') => {
  return useQuery({
    queryKey: ['dashboard', 'spending-trends', period],
    queryFn: () => dashboardService.getSpendingTrends(period),
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
};
```

**Transaction Hooks (`src/hooks/useTransactions.ts`)**
```typescript
export const useTransactions = (filters: TransactionFilter) => {
  return useQuery({
    queryKey: ['transactions', filters],
    queryFn: () => transactionService.getTransactions(filters),
    keepPreviousData: true, // Smooth pagination
    staleTime: 30 * 1000, // 30 seconds
  });
};

export const useCreateTransaction = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: transactionService.createTransaction,
    onMutate: async (newTransaction) => {
      // Optimistic update
      await queryClient.cancelQueries(['transactions']);
      const previousTransactions = queryClient.getQueryData(['transactions']);
      
      queryClient.setQueryData(['transactions'], (old: any) => ({
        ...old,
        data: [newTransaction, ...old.data],
      }));
      
      return { previousTransactions };
    },
    onError: (err, newTransaction, context) => {
      // Rollback optimistic update
      queryClient.setQueryData(['transactions'], context?.previousTransactions);
    },
    onSettled: () => {
      // Refetch to ensure consistency
      queryClient.invalidateQueries(['transactions']);
      queryClient.invalidateQueries(['dashboard']);
    },
  });
};
```

### **State Synchronization Patterns**

#### **Optimistic Updates**
- Immediate UI updates for better perceived performance
- Rollback mechanisms for failed operations
- Conflict resolution strategies
- User feedback for operation status

#### **Real-time Synchronization**
- WebSocket message integration with React Query
- Automatic cache updates from real-time events
- Conflict resolution between local and server state
- Selective re-rendering for performance

#### **Offline Support**
- Cache persistence across sessions
- Offline operation queuing
- Sync on reconnection
- Conflict resolution for offline changes

---

## **8. ML Worker & AI Services**

### **Machine Learning Architecture**

The ML Worker is a sophisticated Python-based service that provides AI-powered transaction categorization using state-of-the-art natural language processing and production-optimized inference.

#### **Core ML Service (`ml-worker/ml_classification_service.py`)**

```python
class TransactionClassifier:
    """
    Intelligent transaction categorization using sentence transformers
    with few-shot learning capabilities
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.sentence_model = None
        self.category_prototypes = {}
        self.user_feedback = {}
        self.scaler = StandardScaler()
        self.onnx_session = None
        self.model_version = "v1.0"
```

**Key Components:**

1. **Sentence Transformer Model**: Uses `all-MiniLM-L6-v2` for text embeddings
2. **Category Prototypes**: Few-shot learning with example transactions
3. **User Feedback System**: Continuous learning from user corrections
4. **ONNX Optimization**: Production-optimized inference engine
5. **Confidence Scoring**: Reliability metrics for predictions

#### **Default Category System**

```python
self.default_categories = {
    "Food & Dining": [
        "coffee starbucks morning",
        "restaurant dinner downtown", 
        "grocery store weekly shopping",
        "fast food lunch break",
        "takeout pizza delivery"
    ],
    "Transportation": [
        "uber ride to airport",
        "gas station fuel up",
        "metro card monthly pass",
        "parking garage downtown",
        "taxi cab fare"
    ],
    "Shopping": [
        "amazon online purchase",
        "target household items",
        "clothing store new shirt",
        "electronics store headphones",
        "pharmacy health supplies"
    ],
    # ... more categories
}
```

**Features:**
- Pre-trained category prototypes for immediate functionality
- User-specific category learning and adaptation
- Hierarchical category support
- Multi-language capability (extendable)

#### **Classification Pipeline**

```python
def classify_transaction(self, description: str, amount: float = None, 
                        merchant: str = None) -> Dict[str, Any]:
    """
    Classify a transaction with confidence scoring
    """
    # 1. Text preprocessing and normalization
    processed_text = self.preprocess_text(description, merchant)
    
    # 2. Feature extraction using sentence transformers
    text_embedding = self.sentence_model.encode([processed_text])
    
    # 3. Similarity computation with category prototypes
    similarities = {}
    for category, prototype in self.category_prototypes.items():
        similarity = cosine_similarity(text_embedding, prototype.reshape(1, -1))[0][0]
        similarities[category] = similarity
    
    # 4. Amount-based feature enhancement
    if amount:
        amount_features = self.extract_amount_features(amount)
        similarities = self.adjust_similarities_by_amount(similarities, amount_features)
    
    # 5. Confidence calculation and prediction
    predicted_category = max(similarities, key=similarities.get)
    confidence = similarities[predicted_category]
    
    # 6. Confidence level classification
    confidence_level = self.classify_confidence(confidence)
    
    return {
        'predicted_category': predicted_category,
        'confidence': float(confidence),
        'confidence_level': confidence_level,
        'all_similarities': similarities,
        'model_version': self.model_version
    }
```

**Confidence Levels:**
- **HIGH** (>0.8): Very confident prediction, auto-apply
- **MEDIUM** (0.6-0.8): Confident prediction, suggest to user
- **LOW** (<0.6): Uncertain prediction, require user input

#### **Production ML Worker (`ml-worker/worker.py`)**

The worker is built on Celery for distributed task processing:

```python
app = Celery('ml_worker')

# Core ML Tasks
@app.task(bind=True, max_retries=3)
def classify_transaction(self, transaction_data: Dict):
    """Classify a single transaction using production-optimized ML system"""
    
@app.task(bind=True, max_retries=3)
def batch_classify_transactions(self, transactions: List[Dict]):
    """Classify multiple transactions in batch"""

@app.task
def collect_user_feedback(feedback_data: Dict):
    """Collect user feedback for model improvement"""

@app.task
def update_model_from_feedback(user_id: str):
    """Update model prototypes based on user feedback"""
```

**Production Features:**
- Automatic retry with exponential backoff
- Error handling and logging
- Performance monitoring
- A/B testing framework
- Model versioning and rollback

#### **Production Orchestrator (`ml-worker/production_orchestrator.py`)**

```python
class ProductionOrchestrator:
    """
    Manages multiple ML model variants in production with A/B testing
    """
    
    def __init__(self, models_config: List[Dict], monitoring_enabled: bool = True,
                 ab_testing_enabled: bool = True):
        self.active_models = {}
        self.model_monitor = ModelMonitor()
        self.ab_framework = ABTestingFramework()
        self.current_experiment_id = None
        
    async def classify_transaction(self, description: str, amount: float,
                                 merchant: str, user_id: str) -> ClassificationResult:
        """
        Route transaction through A/B testing and monitoring
        """
        # 1. Select model variant based on A/B test assignment
        model_variant = self.ab_framework.get_model_assignment(user_id)
        
        # 2. Perform inference with selected model
        result = await self.active_models[model_variant]['engine'].classify(
            description, amount, merchant
        )
        
        # 3. Record metrics and performance data
        await self.model_monitor.record_inference(
            model_variant, result, user_id
        )
        
        return result
```

**Production Capabilities:**
- Multi-model deployment and comparison
- A/B testing for model variants
- Performance monitoring and alerting
- Automatic model selection based on performance
- Canary deployments for new models

#### **ONNX Optimization (`ml-worker/onnx_converter.py`)**

```python
class ONNXConverter:
    """
    Convert and optimize models for production inference
    """
    
    def create_production_models(self, models_dir: str) -> Dict[str, Any]:
        """
        Create optimized ONNX models with quantization
        """
        models = {}
        
        # 1. Standard ONNX conversion
        onnx_path = self.convert_to_onnx(models_dir)
        models['onnx'] = self.create_onnx_engine(onnx_path)
        
        # 2. Quantized ONNX for faster inference
        quantized_path = self.quantize_model(onnx_path)
        models['onnx_quantized'] = self.create_onnx_engine(quantized_path)
        
        # 3. Benchmark all variants
        benchmarks = {}
        for name, engine in models.items():
            benchmarks[name] = engine.benchmark_performance(num_samples=200)
        
        return {
            'models': models,
            'benchmarks': benchmarks
        }
```

**Optimization Features:**
- Dynamic quantization for faster inference
- Graph optimization for reduced memory usage
- Batch processing capabilities
- Hardware-specific optimizations
- Performance benchmarking

#### **Model Monitoring (`ml-worker/model_monitoring.py`)**

```python
class ModelMonitor:
    """
    Comprehensive monitoring for ML models in production
    """
    
    async def record_inference(self, model_name: str, result: ClassificationResult, 
                             user_id: str):
        """Record inference metrics and detect anomalies"""
        
        # Performance metrics
        self.metrics['inference_times'][model_name].append(result.inference_time_ms)
        self.metrics['confidence_scores'][model_name].append(result.confidence)
        
        # Data drift detection
        await self.detect_data_drift(result.input_features)
        
        # Model performance tracking
        await self.update_performance_metrics(model_name, result)
        
        # Anomaly detection
        if self.is_anomalous_prediction(result):
            await self.alert_anomaly(model_name, result, user_id)
    
    def generate_monitoring_report(self) -> Dict[str, Any]:
        """Generate comprehensive monitoring report"""
        return {
            'model_performance': self.calculate_model_performance(),
            'data_drift_analysis': self.analyze_data_drift(),
            'anomaly_summary': self.summarize_anomalies(),
            'resource_usage': self.get_resource_metrics(),
            'recommendations': self.generate_recommendations()
        }
```

**Monitoring Capabilities:**
- Real-time performance tracking
- Data drift detection
- Anomaly detection and alerting
- Resource usage monitoring
- Automated model health reports

#### **A/B Testing Framework (`ml-worker/ab_testing_framework.py`)**

```python
class ABTestingFramework:
    """
    A/B testing framework for ML model experiments
    """
    
    def create_experiment(self, name: str, model_variants: List[str], 
                         traffic_split: Dict[str, float]) -> str:
        """Create new A/B test experiment"""
        
        experiment = {
            'id': str(uuid.uuid4()),
            'name': name,
            'variants': model_variants,
            'traffic_split': traffic_split,
            'start_time': datetime.now(),
            'status': 'active',
            'metrics': defaultdict(list)
        }
        
        self.experiments[experiment['id']] = experiment
        return experiment['id']
    
    def get_model_assignment(self, user_id: str) -> str:
        """Get model variant assignment for user"""
        if not self.current_experiment:
            return self.default_model
        
        # Consistent assignment based on user ID hash
        user_hash = hash(user_id) % 100
        cumulative = 0
        
        for variant, percentage in self.current_experiment['traffic_split'].items():
            cumulative += percentage * 100
            if user_hash < cumulative:
                return variant
        
        return self.default_model
```

**A/B Testing Features:**
- Multi-variant testing support
- Statistical significance testing
- Gradual rollout capabilities
- Performance comparison metrics
- Automated experiment analysis

### **Integration with Backend**

#### **ML Service Integration (`backend/app/services/transaction_service.py`)**

```python
@staticmethod
def create_transaction(db: Session, transaction: TransactionCreate, user_id: int) -> Transaction:
    # If category is not provided, try to predict it
    if not transaction.category_id and transaction.description:
        try:
            # Call the ML service
            with httpx.Client(base_url=settings.ML_SERVICE_URL) as client:
                response = client.post(
                    "/ml/categorise",
                    json={
                        "description": transaction.description,
                        "amount": transaction.amount
                    },
                    timeout=2.0
                )
                response.raise_for_status()
                ml_data = response.json()

            # Check confidence and decide
            if ml_data["confidence"] >= settings.ML_CONFIDENCE_THRESHOLD:
                transaction.category_id = ml_data["category_id"]
            else:
                # Low confidence, ask the user to clarify
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "reason": "low_confidence",
                        "message": "Could not automatically determine the category. Please choose one manually.",
                        "suggested_category_id": ml_data["category_id"],
                        "confidence": ml_data["confidence"],
                    },
                )
        except httpx.RequestError:
            # Service is down or network error
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="The category prediction service is currently unavailable. Please specify a category manually."
            )
```

**Integration Features:**
- Asynchronous ML service calls
- Fallback mechanisms for service unavailability
- Confidence-based decision making
- User feedback collection
- Performance monitoring

---

## **9. Deployment & Infrastructure**

### **Containerization Strategy**

The application uses Docker for containerization with multi-stage builds for optimization:

#### **Backend Dockerfile (`backend/Dockerfile`)**

```dockerfile
FROM python:3.11-slim

# Environment configuration
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# System dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python dependencies
COPY requirements-prod.txt requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements-prod.txt

# Application code
COPY . .

# Security: non-root user
RUN adduser --disabled-password --gecos '' appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Application startup
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Features:**
- Multi-stage build for minimal production image
- Security hardening with non-root user
- Health checks for container orchestration
- Optimized layer caching
- Production-ready configuration

#### **Frontend Dockerfile (`frontend/Dockerfile`)**

```dockerfile
# Multi-stage build for production optimization
FROM node:20-alpine AS base

# Development stage
FROM base AS dev
WORKDIR /app
COPY package.json package-lock.json ./

# ARM64 architecture support
RUN npm cache clean --force && \
    rm -rf node_modules package-lock.json && \
    npm install --force && \
    npm rebuild

COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"]

# Build stage
FROM base AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm cache clean --force && \
    rm -rf node_modules package-lock.json && \
    npm install --force && \
    npm rebuild

COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine AS production
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

**Features:**
- Multi-stage build with development and production targets
- ARM64 architecture compatibility
- Nginx-based production serving
- Optimized static asset delivery
- Development hot-reload support

### **Docker Compose Configuration**

#### **Production Compose (`docker-compose.yml`)**

```yaml
services:
  postgres:
    image: postgres:15-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-postgres}
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-devpassword123}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backend/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-postgres}"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - finance-network

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - finance-network

  backend:
    build: 
      context: ./backend
      dockerfile: Dockerfile
    restart: unless-stopped
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      - REDIS_URL=redis://redis:6379
      - SECRET_KEY=${SECRET_KEY}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - finance-network

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      target: production
    restart: unless-stopped
    depends_on:
      - backend
    networks:
      - finance-network

  ml-worker:
    build:
      context: ./ml-worker
      dockerfile: Dockerfile
    restart: unless-stopped
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      - REDIS_URL=redis://redis:6379
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - finance-network

  nginx:
    image: nginx:alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    depends_on:
      - frontend
      - backend
    networks:
      - finance-network

volumes:
  postgres_data:
  redis_data:

networks:
  finance-network:
    driver: bridge
```

**Features:**
- Service orchestration with health checks
- Persistent data volumes
- Environment variable configuration
- Network isolation
- Automatic restart policies

### **Nginx Configuration (`nginx/nginx.conf`)**

```nginx
events {
    worker_connections 1024;
}

http {
    upstream backend {
        server backend:8000;
    }

    upstream frontend {
        server frontend:3000;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;

    server {
        listen 80;
        server_name localhost;

        # Security headers
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";

        # Frontend routes
        location / {
            proxy_pass http://frontend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # API routes with rate limiting
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            proxy_pass http://backend/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Authentication routes (stricter rate limiting)
        location /api/auth/ {
            limit_req zone=login burst=5 nodelay;
            proxy_pass http://backend/auth/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # WebSocket support
        location /ws {
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

**Features:**
- Reverse proxy for frontend and backend
- Rate limiting for API endpoints
- Security headers for protection
- WebSocket support for real-time features
- Load balancing capabilities
- SSL/TLS termination support

### **Environment Configuration**

#### **Development Environment**
```bash
# Database
DATABASE_URL=postgresql://postgres:devpassword123@localhost:5432/finance_tracker_dev
REDIS_URL=redis://localhost:6379

# Authentication
SECRET_KEY=development-secret-key
JWT_SECRET_KEY=development-jwt-secret
SUPABASE_URL=your-supabase-url
SUPABASE_ANON_KEY=your-supabase-anon-key

# Application
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=debug
ENABLE_DATABASE=true
USE_MOCK_DATA=false
UI_ONLY_MODE=false

# ML Service
ML_SERVICE_URL=http://localhost:8001
ML_CONFIDENCE_THRESHOLD=0.7
```

#### **Production Environment**
```bash
# Database (use strong passwords)
DATABASE_URL=postgresql://user:password@db-host:5432/finance_tracker_prod
REDIS_URL=redis://redis-host:6379

# Authentication (use secure random keys)
SECRET_KEY=production-secret-key-256-bits
JWT_SECRET_KEY=production-jwt-secret-256-bits
SUPABASE_URL=your-production-supabase-url
SUPABASE_ANON_KEY=your-production-supabase-anon-key

# Application
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=info
ENABLE_DATABASE=true

# ML Service
ML_SERVICE_URL=http://ml-worker:8001
ML_CONFIDENCE_THRESHOLD=0.8

# Security
ALLOWED_HOSTS=your-domain.com
CORS_ORIGINS=https://your-domain.com
```

### **Deployment Scripts**

#### **Development Setup (`scripts/dev.sh`)**
```bash
#!/bin/bash
set -e

echo "🚀 Starting Finance Tracker in development mode..."

# Check for required files
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Creating from template..."
    cp .env.example .env
fi

# Start services
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build

echo "✅ Development environment is ready!"
echo "🌐 Frontend: http://localhost:3000"
echo "🔧 Backend API: http://localhost:8000"
echo "📊 API Docs: http://localhost:8000/docs"
```

#### **Production Deployment (`scripts/prod.sh`)**
```bash
#!/bin/bash
set -e

echo "🚀 Deploying Finance Tracker to production..."

# Validate environment
if [ ! -f ".env.prod" ]; then
    echo "❌ Production environment file (.env.prod) not found!"
    exit 1
fi

# Build and deploy
docker-compose --env-file .env.prod -f docker-compose.yml up -d --build

# Health checks
echo "⏳ Waiting for services to be healthy..."
sleep 30

# Verify deployment
if curl -f http://localhost/health > /dev/null 2>&1; then
    echo "✅ Production deployment successful!"
else
    echo "❌ Health check failed!"
    exit 1
fi
```

### **Monitoring & Observability**

#### **Health Checks**
- Application health endpoints
- Database connectivity checks
- External service availability
- ML model health monitoring

#### **Logging Strategy**
- Structured logging with JSON format
- Centralized log aggregation
- Log level configuration by environment
- Request/response logging for debugging

#### **Performance Monitoring**
- Application performance metrics
- Database query performance
- API response times
- ML inference performance

#### **Security Measures**
- Container security scanning
- Dependency vulnerability checks
- Secret management
- Network security policies

---

## **10. Development Workflow**

### **Getting Started**

#### **Prerequisites**
```bash
# Required software
- Docker Desktop (latest version)
- Node.js 18+ (for local frontend development)
- Python 3.11+ (for local backend development)
- Git

# Recommended tools
- VS Code with extensions:
  - Python
  - TypeScript
  - Docker
  - Tailwind CSS IntelliSense
```

#### **Initial Setup**
```bash
# 1. Clone the repository
git clone https://github.com/your-org/finance-tracker.git
cd finance-tracker

# 2. Copy environment configuration
cp .env.example .env

# 3. Start development environment
./scripts/dev.sh

# 4. Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Documentation: http://localhost:8000/docs
```

### **Development Commands**

#### **Docker Commands**
```bash
# Start all services
docker-compose up -d

# Start specific service
docker-compose up backend

# View logs
docker-compose logs -f backend

# Execute commands in container
docker-compose exec backend python -m pytest

# Rebuild services
docker-compose up --build

# Clean up
docker-compose down -v
```

#### **Backend Development**
```bash
# Install dependencies
cd backend
pip install -r requirements-dev.txt

# Run tests
python -m pytest

# Run specific test file
python -m pytest tests/test_transactions.py

# Code formatting
black app/
isort app/

# Type checking
mypy app/

# Database migrations
alembic upgrade head
alembic revision --autogenerate -m "Add new field"
```

#### **Frontend Development**
```bash
# Install dependencies
cd frontend
npm install

# Start development server
npm run dev

# Run tests
npm test

# Type checking
npm run type-check

# Linting and formatting
npm run lint
npm run format

# Build for production
npm run build
```

#### **ML Worker Development**
```bash
# Install dependencies
cd ml-worker
pip install -r requirements.txt

# Start Celery worker
celery -A worker worker --loglevel=info

# Start Celery flower (monitoring)
celery -A worker flower

# Run ML model tests
python -m pytest tests/

# Train model with new data
python scripts/train_model.py
```

### **Code Quality & Standards**

#### **Backend Standards**
- **Code Formatting**: Black with line length 88
- **Import Sorting**: isort with Black compatibility
- **Type Hints**: Comprehensive type annotations
- **Docstrings**: Google-style docstrings
- **Testing**: pytest with >90% coverage
- **API Documentation**: FastAPI automatic OpenAPI

#### **Frontend Standards**
- **Code Formatting**: Prettier with 2-space indentation
- **Linting**: ESLint with TypeScript rules
- **Component Structure**: Functional components with hooks
- **Styling**: Tailwind CSS with consistent design system
- **Testing**: React Testing Library with Jest
- **Type Safety**: Strict TypeScript configuration

#### **Database Standards**
- **Migrations**: Alembic for schema versioning
- **Naming**: Snake_case for tables and columns
- **Indexing**: Performance-optimized indexes
- **Constraints**: Proper foreign key relationships
- **Data Types**: Appropriate types for financial data

### **Testing Strategy**

#### **Backend Testing**
```python
# Unit Tests
class TestTransactionService:
    def test_create_transaction_with_valid_data(self):
        # Test implementation
        pass
    
    def test_ml_integration_with_high_confidence(self):
        # Test ML service integration
        pass

# Integration Tests
class TestTransactionAPI:
    def test_create_transaction_endpoint(self, client, auth_headers):
        response = client.post("/api/transactions/", 
                              json=transaction_data, 
                              headers=auth_headers)
        assert response.status_code == 201

# End-to-End Tests
class TestTransactionFlow:
    def test_complete_transaction_workflow(self, client):
        # Test complete user journey
        pass
```

#### **Frontend Testing**
```typescript
// Component Tests
describe('TransactionForm', () => {
  test('submits transaction with valid data', async () => {
    render(<TransactionForm onSubmit={mockSubmit} />);
    
    await user.type(screen.getByLabelText(/description/i), 'Coffee');
    await user.type(screen.getByLabelText(/amount/i), '4.50');
    await user.click(screen.getByRole('button', { name: /submit/i }));
    
    expect(mockSubmit).toHaveBeenCalledWith({
      description: 'Coffee',
      amount: 4.50,
    });
  });
});

// Integration Tests
describe('Transaction Management', () => {
  test('creates and displays transaction', async () => {
    // Test complete transaction flow
  });
});
```

### **Debugging & Troubleshooting**

#### **Common Issues**

**Database Connection Issues**
```bash
# Check database status
docker-compose logs postgres

# Reset database
docker-compose down -v
docker-compose up postgres

# Manual database connection
docker-compose exec postgres psql -U postgres -d finance_tracker_dev
```

**Frontend Build Issues**
```bash
# Clear node modules and reinstall
rm -rf node_modules package-lock.json
npm install

# Clear build cache
npm run clean
npm run build
```

**ML Service Issues**
```bash
# Check ML worker logs
docker-compose logs ml-worker

# Test ML service directly
curl -X POST http://localhost:8001/ml/categorize \
  -H "Content-Type: application/json" \
  -d '{"description": "coffee shop", "amount": 4.50}'
```

#### **Performance Profiling**

**Backend Performance**
```python
# Add performance middleware
from fastapi import Request
import time

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response
```

**Frontend Performance**
```typescript
// React DevTools Profiler
import { Profiler } from 'react';

function onRenderCallback(id, phase, actualDuration) {
  console.log('Component render time:', { id, phase, actualDuration });
}

<Profiler id="TransactionList" onRender={onRenderCallback}>
  <TransactionList />
</Profiler>
```

### **Deployment Checklist**

#### **Pre-deployment**
- [ ] All tests passing
- [ ] Code review completed
- [ ] Database migrations tested
- [ ] Environment variables configured
- [ ] SSL certificates updated
- [ ] Backup strategy verified

#### **Deployment Process**
1. **Staging Deployment**
   - Deploy to staging environment
   - Run full test suite
   - Performance testing
   - Security scanning

2. **Production Deployment**
   - Database backup
   - Blue-green deployment
   - Health checks
   - Rollback plan ready

3. **Post-deployment**
   - Monitor application metrics
   - Verify all services healthy
   - Check error rates
   - User acceptance testing

### **Maintenance & Updates**

#### **Regular Maintenance**
- **Weekly**: Dependency updates, security patches
- **Monthly**: Performance optimization, database maintenance
- **Quarterly**: Major version updates, architecture review

#### **Monitoring & Alerting**
- Application performance metrics
- Error rate monitoring
- Database performance
- Security vulnerability scanning
- User experience monitoring

---

This comprehensive documentation provides a complete technical overview of the Finance Tracker application, covering all aspects from architecture and implementation to deployment and maintenance. The documentation serves as both a reference for current developers and an onboarding guide for new team members.