# Finance Insights MVP

🚀 **AI-Powered Financial Management Platform** for small businesses and freelancers

Automate financial reporting, track goals, and get AI-driven insights to make smarter business decisions.

---

## ✨ Features

### 💰 Financial Management
- **Transaction Management** - Import, categorize, and manage financial transactions
- **Budgets & Tracking** - Create budgets with recurring support and real-time tracking
- **Labels & Categories** - Organize transactions with custom labels and categories
- **Multi-Currency** - Support for multiple currencies with conversion tracking
- **Recurring Transactions** - Automate recurring income and expenses

### 📊 Projects & Organization
- **Project Tracking** - Track finances by project with 3-level sub-project hierarchy
- **Project Allocations** - Allocate transactions across multiple projects
- **Team Collaboration** - Multi-user support with role-based permissions
- **Organization Management** - Multi-tenant architecture for agencies and teams

### 📈 Reporting & Analytics
- **Interactive Dashboard** - Customizable widgets with drag-and-drop layout
- **Visual Charts** - Revenue/expense trends, pie charts, budget performance, and more
- **Financial Reports** - Comprehensive reporting and analytics
- **Export & PDF** - Export reports and generate PDF invoices

### 🎯 AI Financial Playbook (NEW!)
- **Smart Goal Creation** - Natural language goal input with AI parsing
- **6 Goal Types** - Runway, Savings, Spending Limits, Budget Compliance, Revenue, Profit Margin
- **AI Insights** - Get WHY analysis, recommendations, trend analysis, risk factors, and forecasts
- **What-If Simulator** - Chat-based scenario planning with AI-powered simulations
- **Dashboard Widgets** - View goals and insights directly on your dashboard
- **Progress Tracking** - Visual progress bars, status indicators, and historical tracking

### 💼 Invoicing & Clients
- **Invoice Generation** - Create professional invoices with customizable templates
- **Client Management** - Track clients and invoice history
- **PDF Export** - Generate PDF invoices
- **Payment Tracking** - Track invoice payments and outstanding balances

---

## 📚 Documentation

Comprehensive documentation is available in the **[docs/](docs/)** directory:

### 📖 Start Here
- **[Documentation Index](docs/README.md)** - Complete documentation directory
- **[Quickstart Guide](docs/QUICKSTART.md)** - Get up and running quickly
- **[AI Playbook Guide](docs/playbook/AI_GOAL_COPILOT_README.md)** - Complete AI Playbook specification

### 📁 Documentation Categories
- **[Features](docs/features/)** - Feature documentation, roadmaps, and user guides
- **[Implementations](docs/implementations/)** - Implementation guides and plans
- **[Bug Fixes](docs/fixes/)** - All bug fixes and patches
- **[UI Improvements](docs/ui-improvements/)** - UI/UX enhancements and design updates

### 🎯 AI Playbook Documentation
**Note:** Playbook documentation is being organized - see [docs/README.md](docs/README.md) for the complete index.

Key documents:
- Implementation Status - 100% complete
- Dashboard Widgets Implementation
- Troubleshooting Guides
- AI Integration Documentation

---

## 🛠️ Tech Stack

### Backend
- **Framework:** Django 5.2.7
- **Database:** SQLite (development) / PostgreSQL (production-ready)
- **API:** RESTful API for dashboard widgets and AI services
- **Authentication:** Django built-in with organization-based permissions

### Frontend
- **UI:** HTML5, CSS3, JavaScript (vanilla)
- **Charts:** Chart.js 4.4.0
- **Layout:** Gridstack.js (drag-and-drop dashboard)
- **Animations:** Lottie
- **Icons:** SVG-based icon system

### AI Integration
- **Primary Provider:** OpenAI (GPT-4o-mini)
- **Alternative Providers:** Google Gemini, Groq (free options)
- **Fallback System:** Template-based responses when AI unavailable
- **Use Cases:** Goal parsing, insights generation, what-if simulations, trend analysis

### Deployment
- **Server:** Gunicorn
- **Static Files:** WhiteNoise
- **Supported Platforms:** Heroku, PythonAnywhere, AWS, DigitalOcean

---

## 🚦 Getting Started

### Prerequisites
- Python 3.11+
- pip
- Virtual environment (recommended)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/finance-insights-mvp.git
   cd finance-insights-mvp
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables** (optional but recommended for AI features)
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys:
   # - OPENAI_API_KEY (for AI Playbook features)
   # - SECRET_KEY (Django secret key)
   ```

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create a superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Start the development server**
   ```bash
   python manage.py runserver
   ```

8. **Access the application**
   - Main app: http://127.0.0.1:8000/
   - Admin panel: http://127.0.0.1:8000/admin/

---

## 🎯 Quick Tour

### First Steps
1. **Create an account** - Sign up or log in
2. **Create an organization** - Set up your business/organization
3. **Import transactions** - Add your financial data
4. **Create labels** - Organize your transactions
5. **Set budgets** - Define spending limits
6. **Create projects** - Track project-specific finances
7. **Set financial goals** - Use AI Playbook to set and track goals
8. **Customize dashboard** - Drag and drop widgets to personalize your view

### AI Playbook Quickstart
1. Go to **Playbook** in the navigation
2. Click **Create Goal**
3. Describe your goal in plain English (e.g., "Save £50,000 for equipment by June 2026")
4. Review and confirm the AI-parsed goal
5. Track progress and get AI insights
6. Use the **What-If Simulator** to explore scenarios

---

## 📖 Key Documentation

### Getting Started
- **[Quickstart Guide](docs/QUICKSTART.md)** - Detailed setup and first steps
- **[Feature Roadmap](docs/features/)** - Planned features and enhancements

### Features
- **[AI Financial Playbook](docs/playbook/AI_GOAL_COPILOT_README.md)** - Complete guide to goal tracking and AI insights
- **[Dashboard Widgets](docs/implementations/DASHBOARD_WIDGETS_QUICKSTART.md)** - Customizable dashboard guide
- **[Projects User Guide](docs/features/)** - Project tracking documentation
- **[Team Collaboration](docs/implementations/)** - Multi-user setup and permissions

### Technical
- **[Implementation Status](docs/README.md)** - Complete implementation index
- **[Troubleshooting](docs/README.md#-troubleshooting--fixes)** - Common issues and solutions
- **[Security](docs/README.md#-security-documentation)** - API key management and security

---

## 🔐 Environment Variables

Key environment variables (create a `.env` file):

```bash
# Django
SECRET_KEY=your-secret-key-here
DEBUG=True  # Set to False in production
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (optional - defaults to SQLite)
DATABASE_URL=postgresql://user:pass@localhost/dbname

# AI Features (optional - app works without these)
AI_PLAYBOOK_ENABLED=True
AI_PROVIDER=openai  # Options: openai, gemini, groq
OPENAI_API_KEY=your-openai-key
OPENAI_MODEL=gpt-4o-mini

# Alternative AI Providers (if not using OpenAI)
GEMINI_API_KEY=your-gemini-key
GROQ_API_KEY=your-groq-key
```

**Note:** The application works fully without AI keys - it will use template-based fallbacks for goal insights.

---

## 🚀 Deployment

Ready for production deployment to:
- **Heroku** - See `Procfile` included
- **PythonAnywhere** - WSGI configuration ready
- **AWS / DigitalOcean** - Standard Django deployment
- **Docker** - Dockerization recommended for containerized deployments

See [deployment docs](docs/implementations/) for platform-specific guides.

---

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes with clear commit messages
4. Update documentation
5. Submit a pull request

---

## 📊 Project Status

- **Version:** MVP (1.0)
- **Status:** Production Ready
- **AI Playbook:** 100% Complete
- **Last Major Update:** December 11, 2025
- **Active Development:** ✅ Yes

### Recent Major Features
- ✅ AI Financial Playbook (Dec 2025)
- ✅ Dashboard Widgets System (Nov 2025)
- ✅ Project Hierarchy & Sub-projects (Nov 2025)
- ✅ Team Collaboration (Nov 2025)
- ✅ Invoice Generation & PDF Export (Nov 2025)

---

## 📝 License

This project is licensed under the terms specified in the [LICENSE](LICENSE) file.

---

## 🙏 Acknowledgments

- **Chart.js** - Beautiful, responsive charts
- **Gridstack.js** - Drag-and-drop dashboard layouts
- **OpenAI** - AI-powered insights and natural language processing
- **Django** - Robust, scalable web framework

---

## 📧 Support

- **Documentation:** [docs/README.md](docs/README.md)
- **Issues:** GitHub Issues
- **Email:** [your-email@example.com]

---

**Built with ❤️ for small businesses and freelancers**

---

**Version**: 1.0 MVP  
**Last Updated**: December 11, 2025  
**Status**: ✅ Production Ready

