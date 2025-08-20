# **3. Database Schema & Models**

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

**Insight** - AI-generated financial insights
**MLModelPerformance** - ML model performance tracking

### **Database Relationships Summary**

```
User (1) ──── (M) Account
User (1) ──── (M) Transaction
User (1) ──── (M) Category
User (1) ──── (M) Budget
User (1) ──── (M) Goal


Account (1) ──── (M) Transaction
Category (1) ──── (M) Transaction
Category (1) ──── (M) Budget

Goal (1) ──── (M) GoalContribution
Goal (1) ──── (M) GoalMilestone

Transaction (1) ──── (M) GoalContribution
```

---

### **API Schemas**

The application uses Pydantic models to define the data structures used in the API. These schemas are located in the `backend/app/schemas` directory and are used for data validation, serialization, and documentation.

#### **Common Patterns**

-   **`BaseModel`**: All schemas inherit from Pydantic's `BaseModel`, which provides a solid foundation for creating data models.
-   **`Create`, `Update`, and Response Models**: For each resource, there are typically three types of schemas:
    -   A `Create` schema (e.g., `TransactionCreate`) for creating new resources. These schemas typically exclude fields that are generated by the server, such as `id` and `created_at`.
    -   An `Update` schema (e.g., `TransactionUpdate`) for updating existing resources. These schemas typically have all fields marked as optional, allowing for partial updates.
    -   A response schema (e.g., `Transaction`) for returning data from the API. These schemas represent the full data model, including all server-generated fields.
-   **Data Validation**: Pydantic's validation features are used to enforce data types and constraints, which helps to ensure data consistency and provides clear error messages for invalid data.

#### **Schema Definitions**

-   **`account.py`**: Defines the schemas for bank accounts, including `AccountCreate`, `AccountUpdate`, and `Account`.
-   **`auth.py`**: Contains the schemas for authentication-related data, such as `UserRegister`, `UserLogin`, `RefreshTokenRequest`, and `AuthResponse`.
-   **`budget.py`**: Defines the schemas for budgets, including `BudgetCreate`, `BudgetUpdate`, and `Budget`.
-   **`category.py`**: Contains the schemas for transaction categories, including `CategoryCreate`, `CategoryUpdate`, and `Category`.
-   **`goal.py`**: Defines the schemas for financial goals, including `GoalCreate`, `GoalUpdate`, and `Goal`.
-   **`ml.py`**: Contains the schemas for the machine learning service, such as `MLCategorizationRequest` and `MLCategorizationResponse`.
-   **`transaction.py`**: Defines the schemas for transactions, including `TransactionCreate`, `TransactionUpdate`, and `Transaction`.
-   **`user.py`**: Contains the schemas for user data, such as `UserCreate`, `UserUpdate`, and `User`.
