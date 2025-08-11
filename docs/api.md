# **5. API Routes & Endpoints**

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
