# Codebase Patterns & Best Practices

This document outlines the established patterns and best practices used throughout the Finance Tracker codebase.

## API Layer Patterns

### 1. Response Models & Serialization
- **Pattern**: All API endpoints use FastAPI's `response_model` parameter for automatic serialization
- **Implementation**: Return SQLAlchemy ORM objects directly; FastAPI handles serialization using Pydantic schemas
- **Example**: 
  ```python
  @router.get("", response_model=List[TransactionResponse])
  def get_transactions(...):
      transactions = service.get_transactions(...)
      return transactions  # FastAPI auto-serializes using TransactionResponse schema
  ```

### 2. Exception Handling
- **Pattern**: Use specific custom exceptions instead of broad `except Exception` blocks
- **Implementation**: 
  - Custom exceptions defined in `backend/app/core/exceptions.py`
  - Routers catch specific exceptions (`ValidationException`, `ResourceNotFoundException`, `SQLAlchemyError`)
  - Each exception maps to appropriate HTTP status codes
- **Example**:
  ```python
  try:
      result = service.create_resource(...)
  except ValidationException as e:
      raise HTTPException(status_code=400, detail=str(e))
  except SQLAlchemyError as e:
      logger.error(f"Database error: {str(e)}")
      raise HTTPException(status_code=500, detail="Database operation failed")
  ```

## Server-Side Patterns

### 1. Database Security - Row-Level Security (RLS)
**Pattern**: All user-owned data is protected by PostgreSQL Row-Level Security policies enforced at the database level.

**Implementation**:
- Use `get_db_with_user_context` dependency instead of `get_db` for all protected endpoints
- User context is automatically set via session variable `app.current_user_id`
- RLS policies filter data based on this session variable
- **Required for endpoints handling**: transactions, accounts, budgets, goals, insights, recurring rules, user preferences

**Example**:
```python
# Instead of:
@router.get("/transactions")
def get_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

# Use this pattern:
@router.get("/transactions") 
def get_transactions(
    db: Session = Depends(get_db_with_user_context),
    current_user: User = Depends(get_current_user)
):
```

**Security Benefits**:
- Database-level data isolation prevents accidental data leaks
- Fail-safe: queries without user context return zero rows
- Complementary to application-level security checks

### 2. Performance Optimization
**Guideline**: To prevent N+1 query problems, always use SQLAlchemy's `joinedload` or `selectinload` in service methods when fetching entities with their relationships.

**Implementation**:
```python
# In service methods
query = db.query(Transaction).options(
    joinedload(Transaction.account),
    joinedload(Transaction.category)
).filter(Transaction.user_id == user_id)
```

**Applied in**:
- `TransactionService.get_transactions_with_filters()`
- `BudgetService.get_budgets()`
- `BudgetService.get_budget()`
- `BudgetService.get_budget_alerts()`

### 2. Error Handling
**Guideline**: Service logic should raise specific custom exceptions (e.g., `ResourceNotFoundException`). API routers should catch these and other specific errors (e.g., `SQLAlchemyError`) and return appropriate HTTP status codes. Avoid broad `except Exception` blocks.

**Exception Hierarchy**:
- `BaseAppException`: Base class for all application exceptions
- `ValidationException`: Input validation errors (400 Bad Request)
- `ResourceNotFoundException`: Resource not found errors (404 Not Found)
- `BusinessLogicException`: Business rule violations (422 Unprocessable Entity)
- `ExternalServiceException`: External service failures (503 Service Unavailable)
- `DatabaseException`: Database operation failures (500 Internal Server Error)

## Service Layer Patterns

### 1. Service Structure
- **Pattern**: Static methods for stateless operations, instance methods when state is needed
- **Dependencies**: Database sessions injected via dependency injection
- **Return Types**: Return ORM objects directly, let API layer handle serialization

### 2. Database Operations
- **Transactions**: Use database transactions for multi-step operations
- **Eager Loading**: Always use `joinedload()` or `selectinload()` for related data
- **Filtering**: Accept filter objects and build queries programmatically

## Real-time System Patterns

### 1. WebSocket Management
- **Pattern**: Centralized WebSocket manager handles all connections
- **Implementation**: Redis-based pub/sub system for scalability
- **Message Format**: Standardized JSON messages with `type` and `payload` fields

### 2. Event Broadcasting
- **Pattern**: Services emit events after successful operations
- **Implementation**: WebSocket events sent after database commits
- **Error Handling**: WebSocket failures are logged but don't fail the primary operation

## ML Integration Patterns

### 1. ML Service Integration
- **Pattern**: Async ML service calls with graceful degradation
- **Implementation**: Failed ML calls don't fail primary operations
- **Confidence Thresholds**: Only auto-apply ML results above configured confidence levels

### 2. Model Optimization
- **Pattern**: ONNX export with quantization for production deployment
- **Performance**: CPU-optimized inference with <10ms response times
- **Caching**: Redis caching for category prototypes and frequent lookups

## Security Patterns

### 1. Authentication
- **Pattern**: JWT-based authentication with refresh tokens and secure logout
- **Implementation**: Supabase Auth integration with Redis-based token denylist for immediate invalidation
- **Authorization**: User ID filtering in all data access methods
- **Security Features**: 
  - Immediate token invalidation upon logout using Redis denylist
  - JWT claims extraction (`jti`, `exp`) for precise token tracking
  - Sub-10ms denylist check performance with Redis EXISTS command
  - Graceful degradation if Redis is temporarily unavailable

### 2. Data Access
- **Pattern**: All service methods filter by authenticated user ID
- **Implementation**: User context passed from authentication middleware
- **Isolation**: Users can only access their own data

## Testing Patterns

### 1. Unit Testing
- **Pattern**: Test service methods in isolation
- **Mocking**: Mock external services (ML, Plaid, etc.)
- **Database**: Use test database with proper cleanup

### 2. Integration Testing
- **Pattern**: Test complete request/response cycles
- **Authentication**: Test with actual JWT tokens
- **Real-time**: Test WebSocket message delivery

## Backend Testing Strategy

### 1. Testing Architecture
- **File Structure**: Organized into `tests/unit/` and `tests/integration/` directories
- **Test Isolation**: Each test function gets fresh database via SQLite in-memory fixture
- **Markers**: Tests marked as `@pytest.mark.unit` or `@pytest.mark.integration`
- **Coverage**: Target >75% test coverage for service layer methods

### 2. Unit Testing Patterns
**Purpose**: Test business logic in isolation by mocking all external dependencies

**Structure**:
```python
class TestServiceMethodName:
    def test_method_success_scenario(self, mocker):
        # Arrange - Mock dependencies
        mock_db = MagicMock()
        mock_service_method = mocker.patch('module.external_dependency')
        
        # Act - Call the method
        result = ServiceClass.method(mock_db, test_data)
        
        # Assert - Verify behavior
        assert result.expected_property == expected_value
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
```

**Key Practices**:
- Mock all database operations using `MagicMock()`
- Use `pytest-mock` for patching external services (ML, Plaid, etc.)
- Test multiple scenarios: success, failure, edge cases
- Verify method calls on mocked dependencies
- Never make real database or network calls

### 3. Integration Testing Patterns
**Purpose**: Test complete workflows with real database interactions

**Structure**:
```python
def test_method_integration(self, test_db_session, test_user, test_account):
    # Arrange - Use real database fixtures
    service_data = CreateSchema(...)
    
    # Act - Call service with real database
    result = ServiceClass.method(test_db_session, service_data, test_user.id)
    
    # Assert - Verify data persistence
    assert result.id is not None
    retrieved = test_db_session.query(Model).filter(...).first()
    assert retrieved.property == expected_value
```

**Key Practices**:
- Use `test_db_session` fixture for isolated database
- Create real model instances for test data
- Verify data persistence after operations
- Test user data isolation (users can't access others' data)
- Test complex queries and filtering logic

### 4. Test Database Fixture (conftest.py)
**Central Pattern**: `test_db_session` fixture provides isolated SQLite database

```python
@pytest.fixture(scope="function")
def test_db_session() -> Session:
    engine = create_engine("sqlite:///:memory:", ...)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(...)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
```

**Supporting Fixtures**:
- `test_user`: Creates authenticated user for testing
- `test_account`: Creates user account with sample data
- `test_category`: Creates category for transaction/budget testing
- `sample_*_data`: Provides consistent test data dictionaries

### 5. API Router (Endpoint) Testing
**Purpose**: Test complete HTTP request/response lifecycle including authentication, authorization, and data validation

**Standard Practice**: Use FastAPI's `TestClient` for making mock HTTP requests to the application

**Authentication Pattern**: The `authenticated_api_client` fixture pattern is the standard way to test protected endpoints:

```python
@pytest.fixture(scope="function")
def authenticated_api_client(test_db_session: Session, api_client: TestClient):
    # Create user, login, and return client with auth header
    user_service = UserService(test_db_session)
    user = user_service.create_user(user_data)
    
    response = api_client.post("/auth/login", data=login_data)
    token = response.json()["access_token"]
    
    authenticated_client = TestClient(app)
    authenticated_client.headers["Authorization"] = f"Bearer {token}"
    yield authenticated_client
```

**Router Test Structure**:
```python
class TestRouterName:
    def test_endpoint_success(self, authenticated_api_client: TestClient, test_db_session: Session):
        # Arrange - prepare test data
        request_data = {...}
        
        # Act - make HTTP request
        response = authenticated_api_client.post("/endpoint", json=request_data)
        
        # Assert - verify response
        assert response.status_code == 201
        assert response.json()["field"] == expected_value
        
        # Verify database persistence
        service = Service(test_db_session)
        created_record = service.get_record(...)
        assert created_record is not None
```

**Key Test Scenarios**:
- **Success Cases**: Valid requests receive `2xx` status codes and correct data
- **Authentication**: Protected endpoints return `401 Unauthorized` for unauthenticated requests  
- **Authorization**: Users receive `404 Not Found` when accessing other users' resources
- **Validation**: Invalid request bodies result in `422 Unprocessable Entity` responses
- **Data Persistence**: Verify successful operations are persisted in database
- **User Data Isolation**: Test that users cannot access other users' data

### 6. Testing Best Practices
- **Isolation**: Each test is completely independent
- **Descriptive Names**: Test names describe the scenario being tested
- **AAA Pattern**: Arrange, Act, Assert structure in all tests
- **Edge Cases**: Test boundary conditions, null values, invalid inputs
- **Error Scenarios**: Test exception handling and error conditions
- **Async Testing**: Use `@pytest.mark.asyncio` for async service methods
- **Focus on Layer**: Router tests focus on HTTP layer (routing, auth, validation, serialization) not complex business logic

## Frontend Testing Strategy

### 1. Testing Infrastructure
- **Framework**: Jest with React Testing Library for comprehensive component testing
- **Environment**: jsdom environment for DOM testing with TypeScript support
- **File Organization**: Tests placed in `__tests__` directories alongside components
- **Configuration**: Custom render helpers with provider wrappers for React Query and routing

### 2. Interactive List Component Pattern
**Purpose**: Create rich, expandable list items with self-contained state management

**Implementation**: TransactionItem component demonstrates this pattern:
```typescript
// Expandable list item with local state
export function TransactionItem({ transaction, onEdit, onDelete, showCheckbox, isSelected, onSelect }) {
  const [isExpanded, setIsExpanded] = useState(false); // Local expansion state
  
  return (
    <Card className="hover:shadow-md transition-shadow duration-200">
      <CardContent className="p-4">
        {/* Primary information always visible */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4 flex-1 min-w-0">
            {/* Key information: icon, description, date */}
          </div>
          <div className="flex items-center space-x-4">
            {/* Amount and action buttons including expand/collapse */}
          </div>
        </div>
        
        {/* Expandable secondary details */}
        {isExpanded && (
          <div className="mt-4 pt-4 border-t animate-in slide-in-from-top-2">
            {/* Detailed information in organized sections */}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
```

**Key Principles**:
- **Local State Management**: Use `useState` for component-specific states like expansion
- **Progressive Disclosure**: Show essential info first, details on demand
- **Self-Contained Logic**: Component handles its own interaction states
- **Consistent Interface**: Follow established prop patterns (onEdit, onDelete, etc.)
- **Accessibility**: Proper ARIA labels and keyboard navigation
- **Performance**: Minimal re-renders by keeping state local to component

### 3. Grouped & Collapsible Lists Pattern
**Purpose**: Transform flat data arrays into hierarchical, collapsible group structures for improved data organization and user experience

**Implementation**: Transaction date grouping demonstrates this pattern:
```typescript
// Parent component - data transformation and state management
export function Transactions() {
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());
  
  // Transform flat data into grouped structure using useMemo for performance
  const groupedTransactions = useMemo(() => {
    return transactions.reduce((acc: GroupedTransactions, tx) => {
      const date = tx.transactionDate.split('T')[0]; // Group by YYYY-MM-DD
      if (!acc[date]) {
        acc[date] = { transactions: [], total: 0 };
      }
      acc[date].transactions.push(tx);
      acc[date].total += tx.amountCents;
      return acc;
    }, {});
  }, [transactions]);
  
  // Toggle group expansion
  const toggleGroup = (date: string) => {
    setExpandedGroups(prev => {
      const newSet = new Set(prev);
      if (newSet.has(date)) {
        newSet.delete(date);
      } else {
        newSet.add(date);
      }
      return newSet;
    });
  };
  
  // Initialize with most recent date expanded
  useEffect(() => {
    const dates = Object.keys(groupedTransactions).sort((a, b) => b.localeCompare(a));
    if (dates.length > 0) {
      setExpandedGroups(new Set([dates[0]]));
    }
  }, [groupedTransactions]);
  
  return (
    <TransactionList 
      groupedTransactions={groupedTransactions}
      expandedGroups={expandedGroups}
      onToggleGroup={toggleGroup}
    />
  );
}
```

**Key Principles**:
- **Data Transformation**: Use `useMemo` in parent component for expensive grouping operations
- **State Management**: Use `Set` to track expanded group keys for efficient lookup/toggle
- **Progressive Disclosure**: Groups show summary info, expand to show detailed items  
- **Performance Optimization**: Only re-group data when source data changes
- **Smart Defaults**: Initialize with most relevant group expanded (e.g., most recent date)
- **Consistent Sorting**: Sort groups by relevance (newest first for date grouping)

**List Component Pattern**:
```typescript
// Child component - rendering grouped structure
export function TransactionList({ groupedTransactions, expandedGroups, onToggleGroup }) {
  return (
    <div className="space-y-4">
      {Object.entries(groupedTransactions)
        .sort(([a], [b]) => b.localeCompare(a))
        .map(([date, group]) => {
          const isExpanded = expandedGroups.has(date);
          return (
            <div key={date} className="bg-white rounded-lg shadow-sm">
              {/* Group Header - clickable with summary info */}
              <div 
                className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50"
                onClick={() => onToggleGroup(date)}
              >
                <div className="flex items-center space-x-3">
                  <ChevronDown className={`h-5 w-5 transition-transform ${
                    isExpanded ? 'rotate-0' : '-rotate-90'
                  }`} />
                  <h3 className="font-semibold">{formatGroupDate(date)}</h3>
                </div>
                <div className="text-right">
                  <p className={`font-bold ${group.total >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {formatCurrency(group.total)}
                  </p>
                  <p className="text-sm text-gray-500">{group.transactions.length} transactions</p>
                </div>
              </div>
              
              {/* Collapsible Content */}
              {isExpanded && (
                <div className="px-4 pb-2 border-t border-gray-200">
                  {group.transactions.map(item => (
                    <ItemComponent key={item.id} item={item} {...itemProps} />
                  ))}
                </div>
              )}
            </div>
          );
        })}
    </div>
  );
}
```

**Benefits**:
- **Information Hierarchy**: Users see overview first, details on demand  
- **Reduced Cognitive Load**: Large lists become manageable grouped sections
- **Context Preservation**: Group headers provide temporal/categorical context
- **Performance**: Only expanded groups render their child items
- **Scalability**: Pattern works for date grouping, category grouping, etc.

### 4. Component Testing Patterns
**Purpose**: Test UI components in isolation with proper mocking of dependencies

**File Structure**:
```
src/
├── __tests__/utils/
│   ├── testUtils.tsx      # Custom render with providers
│   └── mockFactories.ts   # Mock data factories
├── pages/__tests__/
│   ├── Dashboard.test.tsx
│   └── Budgets.test.tsx
└── components/[domain]/__tests__/
    └── ComponentName.test.tsx
```

**Custom Render Pattern**:
```typescript
// testUtils.tsx - Standard provider wrapper
const AllTheProviders = ({ children }: { children: React.ReactNode }) => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: 0 } }
  });
  return (
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    </BrowserRouter>
  );
};

const customRender = (ui: ReactElement, options?: RenderOptions) => 
  render(ui, { wrapper: AllTheProviders, ...options });
```

### 3. Hook Mocking Strategies
**Custom Hook Mocking**:
```typescript
// Mock data-fetching hooks
jest.mock('@/hooks/useDashboardAnalytics');
const mockUseDashboardAnalytics = useDashboardAnalytics as jest.MockedFunction<typeof useDashboardAnalytics>;

// Return controlled mock data
mockUseDashboardAnalytics.mockReturnValue({
  data: mockAnalyticsData,
  isLoading: false,
  error: null,
  refetch: jest.fn(),
});
```

**Zustand Store Mocking**:
```typescript
// Mock Zustand stores for real-time testing
jest.mock('@/stores/realtimeStore');
const mockUseRealtimeStore = useRealtimeStore as jest.MockedFunction<typeof useRealtimeStore>;

mockUseRealtimeStore.mockReturnValue({
  isConnected: true,
  recentTransactions: mockTransactions,
  markTransactionsSeen: jest.fn(),
  clearOldTransactions: jest.fn(),
  // ... other store methods
});
```

### 4. Mock Factory Pattern
**Centralized Test Data**:
```typescript
// mockFactories.ts - Reusable mock data generators
export const createMockTransaction = (overrides: Partial<Transaction> = {}): Transaction => ({
  id: 'mock-transaction-1',
  description: 'Coffee Shop',
  amount: 25.50,
  date: '2025-08-12',
  // ... default values
  ...overrides, // Allow customization
});
```

**Benefits**:
- Consistent test data across tests
- Easy customization for specific test scenarios
- Type-safe mock objects
- Reduced duplication in test setup

### 5. Component Testing Scenarios
**Standard Test Categories**:

**Loading States**:
```typescript
it('should display loading skeleton when data is loading', () => {
  mockHook.mockReturnValue({ isLoading: true, data: undefined });
  render(<Component />);
  expect(screen.getAllByRole('generic', { hidden: true })).toHaveLength(4);
});
```

**Error States**:
```typescript
it('should display error message when there is an error', () => {
  mockHook.mockReturnValue({ isError: true, error: new Error('Test error') });
  render(<Component />);
  expect(screen.getByText(/Failed to load/)).toBeInTheDocument();
});
```

**Success States with Data Display**:
```typescript
it('should display data correctly', () => {
  mockHook.mockReturnValue({ data: mockData, isLoading: false });
  render(<Component />);
  expect(screen.getByText('Expected Text')).toBeInTheDocument();
});
```

**User Interactions**:
```typescript
it('should call action when button is clicked', async () => {
  const user = userEvent.setup();
  const mockAction = jest.fn();
  render(<Component onAction={mockAction} />);
  
  await user.click(screen.getByText('Action Button'));
  expect(mockAction).toHaveBeenCalledWith(expectedArgs);
});
```

### 6. Service and API Mocking
**Service Layer Mocking**:
```typescript
// Mock service modules
jest.mock('@/services/budgetService', () => ({
  budgetService: {
    formatCurrency: (cents: number) => `$${(cents / 100).toFixed(2)}`,
    getBudgetStatus: jest.fn().mockReturnValue('on-track'),
    // ... other service methods
  },
}));
```

**Utility Function Mocking**:
```typescript
// Mock utility functions
jest.mock('@/utils', () => ({
  formatCurrency: (amount: number) => `$${(amount / 100).toFixed(2)}`,
  formatRelativeTime: () => '2 minutes ago',
}));
```

### 7. Testing Real-time Components
**WebSocket Component Testing**:
```typescript
// Test real-time updates and WebSocket interactions
it('should display real-time transaction updates', () => {
  const mockTransactions = [createMockTransaction({ isNew: true })];
  mockUseRealtimeStore.mockReturnValue({
    recentTransactions: mockTransactions,
    isConnected: true,
    // ... other real-time state
  });
  
  render(<RealtimeTransactionFeed />);
  expect(screen.getByText('New')).toBeInTheDocument();
});
```

### 8. Form and Filter Testing
**Filter Interaction Testing**:
```typescript
it('should update filters when filter controls change', async () => {
  const user = userEvent.setup();
  render(<FilterComponent />);
  
  const periodSelect = screen.getByDisplayValue('All Periods');
  await user.selectOptions(periodSelect, 'monthly');
  
  await waitFor(() => {
    expect(mockUseBudgets).toHaveBeenCalledWith({ period: 'monthly' });
  });
});
```

### 9. Testing Best Practices
**Key Guidelines**:
- **Test User Behavior**: Focus on what users see and do, not implementation details
- **Mock External Dependencies**: Mock all hooks, services, and external modules
- **Use Factory Pattern**: Create reusable mock data factories for consistency
- **Test All States**: Loading, error, success, and empty states
- **User Event Simulation**: Use `@testing-library/user-event` for realistic interactions
- **Accessibility**: Test with proper ARIA labels and semantic elements
- **Async Testing**: Use `waitFor` for async state changes and effects

**Test File Structure**:
```typescript
describe('ComponentName', () => {
  beforeEach(() => {
    // Setup mocks
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('Rendering States', () => {
    // Loading, error, success state tests
  });

  describe('User Interactions', () => {
    // Click, form submission, filter tests
  });

  describe('Data Display', () => {
    // Content rendering and formatting tests
  });

  describe('Edge Cases', () => {
    // Empty data, boundary conditions
  });
});
```

## Data Auditing Patterns

### 1. Generic Audit Trail System
**Purpose**: Track all data modifications (INSERT, UPDATE, DELETE) across key database tables to maintain data integrity and provide change history.

**Implementation**:
- **Model**: `AuditLog` model in `backend/app/models/audit_log.py`
- **Database Triggers**: PostgreSQL trigger function `log_changes()` automatically captures changes
- **Migration**: `9e561d011f4c_create_audit_log_system.py` creates audit infrastructure
- **Coverage**: Applied to tables: `transactions`, `budgets`, `goals`, `categories`, `accounts`

**Database Schema**:
```sql
CREATE TABLE audit_log (
    id UUID PRIMARY KEY,
    user_id UUID,                    -- User who made the change (null for system actions)
    table_name VARCHAR(100) NOT NULL, -- Table that was modified
    row_id UUID NOT NULL,            -- Primary key of affected record
    action VARCHAR(10) NOT NULL,     -- INSERT, UPDATE, or DELETE
    old_data JSONB,                  -- Complete record state before change (null for INSERT)
    new_data JSONB,                  -- Complete record state after change (null for DELETE)
    created_at TIMESTAMP,            -- When the change occurred
    updated_at TIMESTAMP
);
```

**Trigger Function**:
```sql
CREATE OR REPLACE FUNCTION log_changes()
RETURNS TRIGGER AS $$
DECLARE
    v_old_data jsonb;
    v_new_data jsonb;
    v_user_id uuid;
BEGIN
    -- Try to get user_id from session context
    BEGIN
        v_user_id := current_setting('app.current_user_id')::uuid;
    EXCEPTION WHEN OTHERS THEN
        v_user_id := NULL;
    END;

    -- Log the appropriate change based on trigger operation
    IF (TG_OP = 'UPDATE') THEN
        v_old_data := to_jsonb(OLD);
        v_new_data := to_jsonb(NEW);
        INSERT INTO audit_log (user_id, table_name, row_id, action, old_data, new_data)
        VALUES (v_user_id, TG_TABLE_NAME, OLD.id, 'UPDATE', v_old_data, v_new_data);
        RETURN NEW;
    ELSIF (TG_OP = 'DELETE') THEN
        v_old_data := to_jsonb(OLD);
        INSERT INTO audit_log (user_id, table_name, row_id, action, old_data, new_data)
        VALUES (v_user_id, TG_TABLE_NAME, OLD.id, 'DELETE', v_old_data, NULL);
        RETURN OLD;
    ELSIF (TG_OP = 'INSERT') THEN
        v_new_data := to_jsonb(NEW);
        INSERT INTO audit_log (user_id, table_name, row_id, action, old_data, new_data)
        VALUES (v_user_id, TG_TABLE_NAME, NEW.id, 'INSERT', NULL, v_new_data);
        RETURN NEW;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;
```

### 2. User Context Management
**Pattern**: Pass user context to database triggers for audit attribution

**Implementation**:
```python
# In service methods, set user context before database operations
db.execute(text("SET LOCAL app.current_user_id = :user_id"), {"user_id": str(current_user.id)})
# Then perform database operations - audit trail will capture user_id automatically
```

**Key Features**:
- **User Attribution**: Captures which user made each change
- **System Actions**: Handles system-initiated changes (user_id = NULL)
- **Complete Data Capture**: Stores full record state as JSONB for detailed history
- **Performance Optimized**: Uses indexes on table_name, row_id, and action for efficient queries
- **Generic Design**: Single trigger function works across all audited tables

### 3. Adding Audit to New Tables
**Pattern**: When creating new tables that require audit trails, follow this process:

1. **Create the table** with UUID primary key named `id`
2. **Add trigger** to existing migration or create new migration:
   ```sql
   CREATE TRIGGER [table_name]_audit_trigger
   AFTER INSERT OR UPDATE OR DELETE ON [table_name]
   FOR EACH ROW EXECUTE FUNCTION log_changes();
   ```
3. **Update service layer** to set user context for operations on the table

**Requirements**:
- Table must have UUID primary key named `id`
- Table should follow BaseModel pattern with created_at/updated_at timestamps
- Service methods should set user context via `SET LOCAL app.current_user_id`

## Logging & Monitoring

### 1. Structured Logging
- **Pattern**: Use structured logging with consistent field names
- **Levels**: ERROR for system failures, WARN for recoverable issues, INFO for operations
- **Context**: Include user_id, request_id, and operation context

### 2. Error Tracking
- **Pattern**: All exceptions logged with full context
- **Severity**: Categorized by business impact
- **Alerting**: Critical errors trigger immediate notifications