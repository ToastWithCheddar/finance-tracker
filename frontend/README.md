# Finance Tracker Frontend

A modern, minimalistic React application for personal finance management.

## Tech Stack

- **React 19** with TypeScript
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Utility-first CSS framework
- **React Router** - Client-side routing
- **TanStack Query** - Data fetching and caching
- **React Hook Form** - Form handling
- **Zustand** - State management
- **Lucide React** - Icons

## Project Structure

```
src/
├── components/           # Reusable UI components
│   ├── auth/            # Authentication forms
│   ├── common/          # Common components
│   └── ui/              # Base UI components
├── hooks/               # Custom React hooks
├── layouts/             # Page layouts
├── pages/               # Route components
├── services/            # API and external services
├── stores/              # State management
├── types/               # TypeScript type definitions
└── utils/               # Utility functions
```

## Features

### Authentication
- Login/Register forms with validation
- JWT token management
- Protected routes
- Persistent authentication state

### UI Components
- Responsive design with Tailwind CSS
- Reusable Button, Input, Card components
- Form validation with error handling
- Loading states and animations

### State Management
- Zustand for auth state
- TanStack Query for server state
- Persistent storage for auth tokens

## Getting Started

1. Install dependencies:
```bash
npm install
```

2. Start the development server:
```bash
npm run dev
```

3. Open http://localhost:3000 in your browser (the dev server binds port 3000 — see the `dev` script in `package.json`)

## Environment Variables

Copy `.env.example` to `.env` and configure:

```
VITE_API_URL=http://localhost:8000/api
VITE_APP_NAME="Finance Tracker"
VITE_APP_VERSION="1.0.0"
```

## Build for Production

```bash
npm run build
```

## Tests

The canonical suite is **Vitest** under `frontend/tests/` (services, hooks, stores,
components, utils, with MSW for HTTP mocking). Run it with:

```bash
npm test            # vitest run (what CI executes)
npm run test:watch  # watch mode
npm run type-check  # tsc --noEmit
npm run lint        # eslint
```

## Implemented features

- Authentication (Supabase-backed login/register, protected routes, token refresh)
- Transaction management, categories, and CSV import
- Budgets and budget alerts
- Goals and account reconciliation (Plaid linking)
- Real-time dashboard updates over WebSocket
- Charts/visualizations (Recharts, Nivo) and a responsive layout
- Sentry-backed error reporting and a production-safe logger

This frontend is part of a larger full-stack project — see the
[repository README](../README.md) for architecture and how to run the whole stack.