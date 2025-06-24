# Dhyana - Slack & Jobber Integration

A production-ready dockerized application that integrates Slack and Jobber for seamless business workflow management. Built with React frontend (Vite), Flask backend, PostgreSQL, and Redis.

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  React Frontend │    │  Flask Backend  │    │    PostgreSQL   │
│     (Vite)      │    │   (API/Webhooks)│    │    Database     │
│     Port 5173   │    │    Port 5000    │    │    Port 5432    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                        │                        │
         └────────────────────────┼────────────────────────┘
                                  │
                         ┌─────────────────┐
                         │      Redis      │
                         │   (Sessions)    │
                         │    Port 6379    │
                         └─────────────────┘
```

## ✅ Project Status

- **✅ Backend API Framework** - Complete with Flask, SQLAlchemy, Redis
- **✅ Slack Integration** - Production-ready with comprehensive testing (28 tests passing)
  - OAuth authentication flows
  - Webhook handling (events, interactions, commands)
  - Signature verification and security
  - Interactive components and slash commands
- **✅ Database Models** - Complete with migrations
- **✅ Docker Infrastructure** - Dev/prod profiles with health checks
- **✅ Testing Framework** - Comprehensive pytest setup with mocking
- **🔄 Jobber Integration** - In progress
- **🔄 Frontend Development** - Planned

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 18+ (for local development)
- Python 3.11+ (for local development)

### Setup

1. **Clone and setup environment**
   ```bash
   git clone <repository-url>
   cd dhyana-test
   cp .env.example .env
   ```

2. **Configure environment variables**
   Edit `.env` file with your actual API keys and secrets:
   ```bash
   # Required for Slack integration
   SLACK_BOT_TOKEN=xoxb-your-actual-token
   SLACK_SIGNING_SECRET=your-actual-signing-secret

   # Required for Jobber integration
   JOBBER_API_KEY=your-actual-api-key
   JOBBER_API_SECRET=your-actual-api-secret
   ```

3. **Start the application**
   ```bash
   # Development mode (with hot reloading)
   docker-compose --profile dev up -d

   # Production mode
   docker-compose --profile prod up -d
   ```

### Access Points

- **Frontend**: http://localhost:5173 (dev) or http://localhost (prod)
- **Backend API**: http://localhost:5000
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

## 🧪 Testing

The project includes a comprehensive testing framework with 28+ passing tests covering all Slack integration scenarios.

> **⚠️ CRITICAL: All tests MUST be run inside Docker containers**
>
> This ensures consistent environment, proper database/Redis connections, and reproducible results across all development environments.

### Running Tests (Docker Only)

```bash
# Run all tests (primary command)
docker-compose exec backend pytest

# Run with verbose output
docker-compose exec backend pytest -v

# Run specific test file
docker-compose exec backend pytest backend/tests/test_slack_webhooks.py

# Run with coverage report
docker-compose exec backend pytest --cov=. --cov-report=html

# Run tests matching a pattern
docker-compose exec backend pytest -k "signature_verification"

# ❌ NEVER run tests locally outside Docker - they will fail
# pytest  # DON'T DO THIS
```

### Test Coverage

- **Slack Webhooks**: Complete coverage of events, interactions, and commands
- **Security**: Signature verification and authentication testing
- **Error Handling**: Database errors, API failures, and edge cases
- **Performance**: Concurrent request handling and load testing

For detailed testing practices, see our [Testing Guide](.cursor/rules/testing-practices.mdc).

## 🔧 Development

> **⚠️ All development should be done using Docker containers for consistency**

### Docker-First Development (Recommended)

```bash
# Start development environment
docker-compose --profile dev up -d

# Access backend container for development
docker-compose exec backend bash

# Access frontend container for development
docker-compose exec frontend bash

# View logs while developing
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Local Development (Alternative - Not Recommended for Testing)

If you need to run components locally for development (NOT testing):

1. **Backend (Flask)** - Development only, tests still require Docker
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   flask run
   # ⚠️ Still use: docker-compose exec backend pytest for testing
   ```

2. **Frontend (React)**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

3. **Database Services** - Always required
   ```bash
   docker-compose up postgres redis -d
   ```

### Project Structure

```
dhyana-test/
├── backend/
│   ├── models/          # Database models (Slack, Jobber entities)
│   ├── routes/          # API routes & webhook handlers
│   ├── utils/           # Slack/Jobber API clients
│   ├── tests/           # Comprehensive test suite
│   ├── app.py           # Flask application
│   ├── config.py        # Configuration management
│   └── requirements.txt # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/  # React components
│   │   ├── pages/       # Page components
│   │   ├── services/    # API services
│   │   └── utils/       # Utility functions
│   ├── vite.config.js   # Vite configuration
│   └── package.json     # Node dependencies
├── .cursor/rules/       # Development guidelines and practices
├── docker-compose.yml   # Docker services configuration
├── .gitignore          # Git ignore patterns
└── .env.example        # Environment template
```

## 🎯 Features

### Slack Integration ✅ Production Ready
- **OAuth Authentication**: Complete authorization flow
- **Event Handling**: Real-time message processing and app mentions
- **Interactive Components**: Buttons, modals, and shortcuts
- **Slash Commands**: `/jobber` command with parameter support
- **Security**: Signature verification and request validation
- **Error Handling**: Graceful failure handling and logging

### Jobber Integration 🔄 In Progress
- API authentication and data synchronization
- Client management (CRUD operations)
- Job tracking and status updates
- Invoice handling and processing
- Webhook processing for real-time updates

### API Endpoints

#### Authentication
- `GET /auth/slack/install` - Initiate Slack OAuth
- `GET /auth/slack/oauth` - Slack OAuth callback
- `POST /auth/jobber/auth` - Jobber API authentication
- `GET /auth/status` - Check authentication status

#### Slack API
- `GET /api/slack/teams` - List Slack teams
- `GET /api/slack/teams/{id}/users` - List team users
- `GET /api/slack/teams/{id}/channels` - List team channels

#### Jobber API
- `GET /api/jobber/clients` - List clients
- `POST /api/jobber/clients` - Create client
- `PUT /api/jobber/clients/{id}` - Update client
- `DELETE /api/jobber/clients/{id}` - Delete client
- `GET /api/jobber/jobs` - List jobs
- `GET /api/jobber/invoices` - List invoices

#### Webhooks
- `POST /webhooks/slack/events` - Slack events (messages, mentions, etc.)
- `POST /webhooks/slack/interactions` - Slack interactions (buttons, modals)
- `POST /webhooks/slack/commands` - Slack slash commands
- `POST /webhooks/jobber/webhooks` - Jobber webhooks

## 🛠️ Configuration

### Slack App Setup

1. Create a Slack app at https://api.slack.com/apps
2. Configure OAuth & Permissions:
   - Add redirect URL: `http://localhost:5000/auth/slack/oauth`
   - Required scopes: `channels:read`, `chat:write`, `commands`, `users:read`
3. Enable Events API:
   - Request URL: `http://localhost:5000/webhooks/slack/events`
   - Subscribe to: `message.channels`, `app_mention`, `team_join`, `channel_created`
4. Add Slash Commands:
   - Command: `/jobber`
   - Request URL: `http://localhost:5000/webhooks/slack/commands`
5. Enable Interactive Components:
   - Request URL: `http://localhost:5000/webhooks/slack/interactions`

### Jobber API Setup

1. Get API credentials from Jobber dashboard
2. Configure webhook URL: `http://localhost:5000/webhooks/jobber/webhooks`
3. Subscribe to relevant events (client updates, job status changes, etc.)

## 🔄 Docker Commands

```bash
# Start all services
docker-compose up -d

# Start specific services
docker-compose up postgres redis -d

# Development with hot reloading
docker-compose --profile dev up -d

# Production build
docker-compose --profile prod up -d

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Run tests
docker-compose exec backend pytest

# Stop all services
docker-compose down

# Rebuild services
docker-compose build --no-cache

# Reset database
docker-compose down -v
docker-compose up -d
```

## 🗃️ Database

The application uses PostgreSQL with the following main tables:

- `slack_teams` - Slack workspace information
- `slack_users` - Slack user data and profiles
- `slack_channels` - Slack channel metadata
- `slack_messages` - Message history and content
- `jobber_clients` - Jobber client information
- `jobber_jobs` - Job data and status tracking
- `jobber_invoices` - Invoice information and payment status

## 🔐 Security

- **Environment Variables**: All secrets managed via environment variables
- **Slack Signature Verification**: All webhooks verify request signatures
- **Non-root Docker Users**: Security-hardened container execution
- **CORS Configuration**: Proper cross-origin request handling
- **Session Management**: Redis-backed session storage
- **Request Validation**: Input sanitization and validation

## 📊 Performance

- **Concurrent Request Handling**: Tested with multiple simultaneous webhooks
- **Database Connection Pooling**: Efficient database resource management
- **Redis Caching**: Fast session and data caching
- **Docker Health Checks**: Automatic service health monitoring

## 📝 Contributing

1. Fork the repository
2. Create a feature branch
3. Follow our [Coding Standards](.cursor/rules/coding-standards.mdc)
4. Write comprehensive tests following our [Testing Practices](.cursor/rules/testing-practices.mdc)
5. Ensure all tests pass: `docker-compose exec backend pytest`
6. Test in both development and production profiles
7. Submit a pull request

## 🐛 Troubleshooting

### Common Issues

1. **Port conflicts**: Ensure ports 5000, 5173, 5432, 6379 are available
2. **Database connection**: Check PostgreSQL is running and credentials are correct
3. **Slack webhooks**: Ensure your app is accessible from the internet for webhooks
4. **Test failures**: Run `docker-compose exec backend pytest -v` for detailed output (tests MUST run in Docker)

### Health Checks

```bash
# Check backend health
curl http://localhost:5000/health

# Check frontend health (when implemented)
curl http://localhost:5173/health

# Check database
docker-compose exec postgres pg_isready

# Check Redis
docker-compose exec redis redis-cli ping

# Run diagnostic tests
docker-compose exec backend pytest backend/tests/ -v
```

### Debugging

```bash
# View detailed logs
docker-compose logs -f backend

# Run tests with debugging
docker-compose exec backend pytest --pdb

# Check database connections
docker-compose exec backend python -c "from app import db; print(db.engine.execute('SELECT 1').fetchone())"
```

## 📚 Documentation

- [Project Structure](.cursor/rules/project-structure.mdc) - Detailed architecture overview
- [Coding Standards](.cursor/rules/coding-standards.mdc) - Development best practices
- [API Conventions](.cursor/rules/api-conventions.mdc) - API design guidelines
- [Testing Practices](.cursor/rules/testing-practices.mdc) - Comprehensive testing guide
- [Development Workflow](.cursor/rules/development-workflow.mdc) - Setup and deployment

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Recent Updates

- ✅ **Slack Integration Complete**: 28 comprehensive tests passing
- ✅ **Security Hardened**: Complete signature verification implementation
- ✅ **Testing Framework**: Comprehensive pytest setup with fixtures and mocking
- ✅ **Docker Infrastructure**: Production-ready containerization
- ✅ **Documentation**: Complete rule-based development guidelines