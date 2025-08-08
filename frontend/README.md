# Finance Tracker Frontend

A modern, minimalistic React application for personal finance management.

## Tech Stack

- **React 18** with TypeScript
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

3. Open http://localhost:5173 in your browser

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

## Features Implemented (Day 4)

✅ React + Vite + TypeScript setup
✅ Tailwind CSS configuration
✅ Basic routing structure
✅ TanStack Query setup
✅ Authentication components
✅ Protected routes
✅ State management with Zustand
✅ Responsive dashboard layout
✅ Form validation
✅ Error handling

## Next Steps (Days 5+)

- [ ] Transaction management
- [ ] Category system
- [ ] Budget tracking
- [ ] Real-time updates
- [ ] Chart components
- [ ] Mobile optimization
- [ ] PWA features