# Frontend Architecture and Design

This document provides a comprehensive analysis of the finance tracker application's frontend architecture, design patterns, and key implementation details.

## 1. Application Architecture Overview

The finance tracker frontend is a modern single-page application (SPA) built with **React** and **TypeScript**. It leverages a robust set of libraries and patterns to ensure a scalable, maintainable, and responsive user experience.

*   **Core Framework**: React (with Vite for fast development).
*   **Language**: TypeScript for strong typing and improved code quality.
*   **Routing**: `react-router-dom` for declarative client-side navigation.
*   **State Management**:
    *   **React Query (`@tanstack/react-query`)**: Primary tool for server-state management (data fetching, caching, synchronization, and mutations). It significantly reduces boilerplate for data operations and provides powerful caching mechanisms.
    *   **Zustand**: Lightweight and flexible state management library used for global client-side state, specifically for authentication (`authStore`) and real-time data (`realtimeStore`).
*   **UI Library**: Custom UI components built with **Tailwind CSS** for styling, promoting consistency and rapid development.
*   **API Communication**: A custom `apiClient` handles all interactions with the backend API, including authentication, token management, and structured error handling.
*   **Real-time Communication**: WebSockets are utilized for live updates, managed through a dedicated hook and Zustand store.
*   **Code Structure**: Organized into logical modules (`components`, `pages`, `hooks`, `services`, `stores`, `utils`, `types`) to enhance modularity and separation of concerns.

## 2. Component Structure and Patterns

The application follows a clear component-based architecture, with components organized by their purpose and domain.

*   **`App.tsx`**: The root component, responsible for setting up the global context providers (React Query, Toast), authentication initialization, and defining the main routing structure.
*   **`pages/`**: Contains top-level components that represent distinct views or screens of the application (e.g., `Dashboard`, `Transactions`, `Settings`, `Login`). These components often orchestrate data fetching and display other, smaller components.
*   **`components/`**: Houses reusable UI components. This directory is further subdivided into domain-specific folders:
    *   **`components/ui/`**: Fundamental, generic UI building blocks (e.g., `Button`, `Input`, `Card`, `Modal`, `LoadingSpinner`, `Toast`, `ThemeToggle`, `Alert`). These are highly reusable and styled with Tailwind CSS.
    *   **`components/accounts/`**: Components related to managing bank accounts (e.g., `AccountReconciliation`, `AccountSyncStatus`, `AccountsList`).
    *   **`components/auth/`**: Authentication-related forms (e.g., `LoginForm`, `RegisterForm`).
    *   **`components/budgets/`**: Components for budget management (e.g., `BudgetCard`, `BudgetForm`).
    *   **`components/categories/`**: Components for category selection (e.g., `CategorySelector`).
    *   **`components/common/`**: General-purpose components like `ErrorBoundary` (for UI error handling), `ProtectedRoute` (for route protection), and `AuthInitializer` (for app startup authentication checks).
    *   **`components/dashboard/`**: Specific widgets and charts for the dashboard (e.g., `CategoryPieChart`, `MonthlyComparisonChart`, `RealtimeDashboard`, `NotificationPanel`, `RealtimeTransactionFeed`).
    *   **`components/goals/`**: Components for managing financial goals (e.g., `GoalCard`, `GoalForm`, `GoalsDashboard`, `MilestoneNotification`).
    *   **`components/layout/`**: Defines the overall application layout and navigation (`Navigation`).
    *   **`components/plaid/`**: Integrates with the Plaid API for bank connections (`PlaidLink`, `AccountConnectionStatus`).
    *   **`components/transactions/`**: Components for transaction management (e.g., `CSVImport`, `MLCategoryFeedback`, `TransactionFilters`, `TransactionForm`, `TransactionList`).

## 3. State Management Implementation

The application employs a hybrid state management approach, combining React Query for server-state and Zustand for client-side global state.

### React Query (`@tanstack/react-query`)

*   **Purpose**: Manages asynchronous data operations (fetching, caching, invalidation, synchronization, and mutations) with the backend API. It eliminates the need for manual loading states, error handling, and complex data fetching logic in components.
*   **Configuration**: `services/queryClient.ts` sets up the `QueryClient` with default options for `staleTime`, `gcTime`, `retry` logic, and global error handling (e.g., logging out on 401 Unauthorized errors).
*   **Usage**: Custom hooks in `hooks/` (e.g., `useAccounts`, `useBudgets`, `useTransactions`) wrap `useQuery` and `useMutation` to provide domain-specific data access. These hooks define `queryKeys` for efficient caching and invalidation.
*   **Cache Management**: `hooks/useAuthCacheManagement.ts` ensures that the React Query cache is cleared when the user's authentication state changes (e.g., login, logout, user switch) to prevent stale data from being displayed.

### Zustand

*   **Purpose**: Manages global client-side state that is not directly tied to server data, or for real-time updates that need immediate reflection. It's lightweight and provides a simple API for creating stores.
*   **`stores/authStore.ts`**:
    *   **State**: `user` (User object), `isAuthenticated` (boolean), `isLoading` (boolean), `error` (string).
    *   **Actions**: `login`, `register`, `logout`, `refreshToken`, `updateUser`, `checkTokenExpiration`.
    *   **Persistence**: Uses `localStorage` to persist `user` and `isAuthenticated` state across browser refreshes.
*   **`stores/realtimeStore.ts`**:
    *   **State**: `isConnected`, `connectionStatus`, `recentTransactions`, `transactionUpdates`, `milestoneAlerts`, `goalCompletions`, `goalUpdates`, `notifications`, `budgetAlerts`.
    *   **Actions**: `updateConnectionStatus`, `addRecentTransaction`, `markTransactionsSeen`, `addNotification`, `markNotificationRead`, `handleWebSocketMessage` (main entry point for WebSocket events), etc.
    *   **Middleware**: `subscribeWithSelector` allows components to subscribe to specific state changes.
*   **`stores/themeStore.ts`**:
    *   **State**: `theme` (user preference: 'light' | 'dark' | 'auto'), `systemTheme` ('light' | 'dark'), `actualTheme` (resolved theme applied to DOM).
    *   **Actions**: `setTheme`, `initializeTheme`, `applyTheme`.
    *   **Persistence**: Stores `theme-preference` in `localStorage`.

## 4. API Integration Patterns

Frontend-backend communication is centralized and follows a structured pattern.

*   **`services/api.ts` (`ApiClient`)**:
    *   **Core Functionality**: This class is the central point for all HTTP requests. It wraps the native `fetch` API.
    *   **Authentication**: Automatically attaches `Authorization: Bearer <token>` headers to requests using tokens retrieved from `secureStorage`.
    *   **Token Refresh**: Implements a silent token refresh mechanism. If a 401 Unauthorized response is received and a refresh token is available, it attempts to refresh the access token before retrying the original request.
    *   **Error Handling**: Provides structured error handling, parsing API error responses into specific error types (`ValidationError`, `NetworkError`, `AuthError`, `BusinessError`, `SystemError`) for easier consumption by the application.
    *   **CSRF Protection**: Integrates with `csrfService` to include CSRF tokens in request headers.
    *   **Mocking**: Can operate in a "mock data" or "UI only" mode (`services/mockApiClient.ts`) for frontend development without a running backend.

*   **`services/base/BaseService.ts`**:
    *   **Abstraction Layer**: Provides a base class for all domain-specific services. It encapsulates common API interaction logic (e.g., `get`, `post`, `put`, `delete`, `getPaginated`, `postFormData`, `getBlob`).
    *   **Caching**: Includes a basic in-memory caching mechanism for GET requests, which can be enabled per request.
    *   **Error Propagation**: Standardizes error handling by catching `ApiClient` errors and re-throwing them with additional service-specific context.

*   **Domain-Specific Services (`services/*.ts`)**:
    *   Classes like `AccountService`, `BudgetService`, `CategoryService`, `TransactionService`, `PlaidService`, `GoalService`, `UserPreferencesService`, and `MLService` extend `BaseService`.
    *   Each service defines methods for CRUD operations and other domain-specific interactions with their respective backend endpoints. They handle data serialization/deserialization and type conversions (e.g., cents to dollars).

## 5. Routing and Navigation

The application uses `react-router-dom` for navigation, providing a smooth single-page application experience.

*   **`App.tsx`**: The main routing configuration is defined here using `BrowserRouter`, `Routes`, and `Route` components.
*   **Protected Routes**: Most application routes (e.g., `/dashboard`, `/transactions`) are wrapped within a `ProtectedRoute` component.
*   **`components/common/ProtectedRoute.tsx`**: This component checks the user's authentication status (`useIsAuthenticated` from `authStore`). If the user is not authenticated, they are redirected to the `/login` page. A loading spinner is shown while the authentication status is being determined.
*   **Navigation (`components/layout/Navigation.tsx`)**: Provides the main application navigation links, using `NavLink` from `react-router-dom` to highlight the active route. It also displays user information and a logout button.

## 6. Key Areas - Detailed Breakdown

### Components

*   **`components/ui/`**:
    *   **Purpose**: Provides a consistent and reusable set of basic UI elements.
    *   **Examples**: `Button` (with variants, sizes, loading states), `Input` (with labels, error messages), `Card` (for content grouping), `Modal` (for overlays), `LoadingSpinner` (for visual feedback), `Toast` (for transient messages), `ThemeToggle` (for dark/light mode).
    *   **Styling**: All components are styled using Tailwind CSS classes, often combined with `clsx` and `tailwind-merge` for conditional styling.
*   **Domain-Specific Components**: Each domain (accounts, budgets, transactions, etc.) has its own folder within `components/` containing components specific to that domain's UI and functionality. These components often consume data from custom hooks and interact with services.

### Pages/Views

*   **Purpose**: Represent the main screens of the application. They typically compose multiple smaller components and orchestrate data flow for that specific view.
*   **Examples**:
    *   `Dashboard.tsx`: Displays an overview of financial data, including charts (`CategoryPieChart`, `MonthlyComparisonChart`), real-time transaction feeds (`RealtimeTransactionFeed`), and notifications (`NotificationPanel`). It uses `useDashboardAnalytics` and `useRealtimeStore`.
    *   `Transactions.tsx`: Manages all user transactions. It includes `TransactionFilters`, `TransactionList`, `TransactionForm` (for add/edit), and `CSVImport`. It heavily relies on `useTransactions` and `useTransactionActions`.
    *   `Settings.tsx`: Allows users to customize their application preferences, using `useUserPreferences` and `usePreferencesActions`.

### Services/API

*   **Purpose**: Encapsulate all logic for interacting with the backend API. They provide a clean, type-safe interface for components and hooks to fetch and manipulate data.
*   **Core**: `api.ts` (`ApiClient`) is the HTTP client.
*   **Base**: `base/BaseService.ts` provides common methods and error handling.
*   **Domain-Specific**: `accountService.ts`, `budgetService.ts`, `categoryService.ts`, `dashboardService.ts`, `goalService.ts`, `plaidService.ts`, `transactionService.ts`, `userPreferencesService.ts`, `mlService.ts`. Each service maps to a specific backend domain and exposes methods for data operations.
*   **Standardization**: `ServiceRegistry.ts` and `standardized/` services (`StandardizedTransactionService`, `StandardizedBudgetService`) are being introduced to provide a more consistent and robust service layer with explicit success/error results.

### State Management (Zustand Stores)

*   **`stores/authStore.ts`**:
    *   **State**: `user` (User object), `isAuthenticated` (boolean), `isLoading` (boolean), `error` (string).
    *   **Actions**: `login`, `register`, `logout`, `refreshToken`, `updateUser`, `checkTokenExpiration`.
    *   **Persistence**: Uses `localStorage` to persist `user` and `isAuthenticated` state across sessions.
*   **`stores/realtimeStore.ts`**:
    *   **State**: `isConnected`, `connectionStatus`, `recentTransactions`, `transactionUpdates`, `milestoneAlerts`, `goalCompletions`, `goalUpdates`, `notifications`, `budgetAlerts`.
    *   **Actions**: `updateConnectionStatus`, `addRecentTransaction`, `markTransactionsSeen`, `addNotification`, `markNotificationRead`, `handleWebSocketMessage` (main entry point for WebSocket events), etc.
    *   **Middleware**: `subscribeWithSelector` allows components to subscribe to specific state changes.
*   **`stores/themeStore.ts`**:
    *   **State**: `theme` (user preference: 'light' | 'dark' | 'auto'), `systemTheme` ('light' | 'dark'), `actualTheme` (resolved theme applied to DOM).
    *   **Actions**: `setTheme`, `initializeTheme`, `applyTheme`.
    *   **Persistence**: Stores `theme-preference` in `localStorage`.

### Hooks

*   **Purpose**: Encapsulate reusable logic, often integrating with React Query or Zustand, to provide data and functionality to components.
*   **Data Fetching Hooks (`hooks/useAccounts.ts`, `useBudgets.ts`, etc.)**:
    *   Wrap `useQuery` and `useMutation` from React Query.
    *   Define `queryKey` arrays for caching.
    *   Handle `onSuccess` and `onError` callbacks for cache invalidation and side effects (e.g., showing toasts).
*   **Authentication Hooks**: `useAuthUser`, `useIsAuthenticated`, `useAuthLoading`, `useAuthError` are selector hooks from `authStore` for efficient state access.
*   **Real-time Hooks**: `useWebSocket.ts` manages the WebSocket connection. Selector hooks from `realtimeStore` (e.g., `useConnectionStatus`, `useRealtimeTransactions`, `useNotifications`) provide access to real-time data.
*   **Utility Hooks**:
    *   `useAuthCacheManagement.ts`: Clears React Query cache on auth state changes.
    *   `usePlaidActions.ts`: Combines Plaid-related mutations (`exchangeToken`, `syncTransactions`, `syncBalances`).
    *   `useTransactionActions.ts`: Combines transaction-related mutations (CRUD, import, export).
    *   `useUserPreferences.ts`: Provides access to user preferences and actions to update them.

### Utils

*   **Purpose**: Provide general-purpose helper functions that are not tied to specific React components or API services.
*   **Examples**:
    *   `cn.ts`: A helper for conditionally combining Tailwind CSS classes.
    *   `currency.ts`: Functions for converting between cents and dollars, and formatting currency for display.
    *   `validation.ts`: Utility functions for validating various data types (emails, UUIDs, dates, amounts).
    *   `index.ts`: Re-exports common utilities.
    *   `envValidation.ts`: Validates environment variables at application startup.
    *   `formatDate`, `formatRelativeTime`, `debounce`, `generateId`, `truncate`, `isEmpty`: General utility functions for common tasks.

### Types

*   **Purpose**: Define the shape of data used throughout the application, ensuring type safety and improving code readability and maintainability.
*   **Location**: Primarily in the `types/` directory, with separate files for different domains (e.g., `auth.ts`, `transaction.ts`, `category.ts`, `budgets.ts`, `goals.ts`, `api.ts`, `errors.ts`, `websocket.ts`, `ml.ts`).
*   **Content**: Includes interfaces for API request/response bodies, domain models, state structures, and utility types.
*   **Error Types**: A comprehensive error type system (`errors.ts`) defines various categories of errors (validation, network, auth, business, system) for structured error handling.
*   **WebSocket Types**: Detailed type definitions for WebSocket messages (`websocket.ts`) ensure type-safe handling of real-time events.
