# Personal Finance Tracker (Development Setup)

🚨 **DEVELOPMENT VERSION ONLY** 🚨

This is a development-focused setup of a personal finance management application with AI-powered insights. This configuration is optimized for development and testing, **NOT for production use**.

## 🚀 Development Quick Start

**Run the entire development stack:**

```bash
# 1. Clone the repository
git clone <repo-url>
cd finance-tracker

# 2. Start development environment (creates .env automatically)
./scripts/dev.sh
```

**Or manually:**
```bash
# Create .env from example (has safe development defaults)
cp .env.example .env

# Start all services in development mode
docker-compose up --build
```

**Access the development application:**
- 📱 **Frontend**: http://localhost:3000 (with hot reload)
- 🔧 **Backend API**: http://localhost:8000 (with auto-reload)
- 📊 **API Docs**: http://localhost:8000/docs (always enabled)
- 🗄️ **PostgreSQL**: localhost:5432 (database: finance_tracker_dev)
- 📦 **Redis**: localhost:6379
- 🤖 **ML Worker**: http://localhost:8001

**Development commands:**
```bash
# Stop all services
docker-compose down

# Fresh restart (clears volumes)
docker-compose down -v && ./scripts/dev.sh

# View logs
docker-compose logs -f [service-name]

# Shell access
docker-compose exec [service-name] bash
```

## Features

- **Transaction Tracking & Categorization:**  
  Log your income and expenses. Transactions are automatically categorized using AI, with the option to manually adjust categories for accuracy.

- **Budget Management with Real-Time Alerts:**  
  Set monthly or custom budgets for different spending categories. Receive instant notifications when you approach or exceed your budget limits.

- **AI-Powered Spending Insights:**  
  Access personalized analytics on your spending habits, trends, and receive actionable suggestions for saving, powered by integrated machine learning models.

- **Multi-Account Support:**  
  Connect and manage multiple bank accounts and cards in one place. View consolidated balances and transaction histories across all accounts.

- **Real-Time Updates:**  
  All data, analytics, and insights update instantly as you add or modify transactions, ensuring you always have the latest information.

- **Data Visualization:**  
  Interactive charts and graphs help you visualize your spending, income, and budget progress for better financial understanding.

- **Authentication (Development Mode):**  
  Basic authentication with development-friendly settings. Admin bypass enabled for testing.

- **Import/Export Functionality:**  
  Easily import transactions from CSV files and export your financial data for backup or further analysis.

- **Mobile-Friendly UI:**  
  Enjoy a responsive design that works seamlessly on both desktop and mobile devices.

## Tech Stack (Development Configuration)
- **Frontend**: React + TypeScript + Tailwind CSS + Vite (with HMR)
- **Backend**: FastAPI + PostgreSQL (with auto-reload)
- **ML**: Scikit-learn + Pandas
- **Infrastructure**: Docker + Redis
- **Development**: Hot reload, debug logging, relaxed security

## Development Features

✅ **Hot Module Replacement (HMR)** - Frontend changes reload instantly  
✅ **Auto-reload** - Backend restarts on code changes  
✅ **Debug logging** - Detailed logs for troubleshooting  
✅ **Relaxed security** - CORS, rate limiting, and auth bypass for testing  
✅ **Development database** - Separate `finance_tracker_dev` database  
✅ **Always-on docs** - API documentation always available  
✅ **Source maps** - For debugging in browser dev tools  

## ⚠️ Important Notes

- **NOT FOR PRODUCTION**: This setup has relaxed security settings
- **Development database**: Uses `finance_tracker_dev` database
- **Weak secrets**: Uses predictable development keys
- **Debug enabled**: Detailed error messages and logs
- **CORS disabled**: Allows all origins for development

## Development

See `/docs/setup.md` for detailed setup instructions and development workflows.