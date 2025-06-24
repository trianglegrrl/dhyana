# Slack & Jobber Integration App

A dockerized application that integrates Slack and Jobber for seamless business workflow management. Built with React frontend (Vite), Flask backend, PostgreSQL, and Redis.

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

## 🔧 Development

### Running Locally

1. **Backend (Flask)**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   flask run
   ```

2. **Frontend (React)**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

3. **Database**
   ```bash
   docker-compose up postgres redis -d
   ```

### Project Structure

```
dhyana-test/
├── backend/
│   ├── models/          # Database models
│   ├── routes/          # API routes & webhooks
│   ├── utils/           # Utility functions
│   ├── app.py           # Flask application
│   ├── config.py        # Configuration
│   └── requirements.txt # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/  # React components
│   │   ├── pages/       # Page components
│   │   ├── services/    # API services
│   │   └── utils/       # Utility functions
│   ├── vite.config.js   # Vite configuration
│   └── package.json     # Node dependencies
├── docker-compose.yml   # Docker services
└── .env.example         # Environment template
```

## 🎯 Features

### Slack Integration
- OAuth authentication
- Webhook handling for events
- Slash commands (`/jobber`)
- Interactive components
- Message processing

### Jobber Integration
- API authentication
- Client management (CRUD)
- Job tracking
- Invoice handling
- Webhook processing

### API Endpoints

#### Authentication
- `GET /auth/slack/install` - Initiate Slack OAuth
- `GET /auth/slack/oauth` - Slack OAuth callback
- `POST /auth/jobber/auth` - Jobber API authentication
- `GET /auth/status` - Check auth status

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
- `POST /webhooks/slack/events` - Slack events
- `POST /webhooks/slack/interactions` - Slack interactions
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
4. Add Slash Commands:
   - Command: `/jobber`
   - Request URL: `http://localhost:5000/webhooks/slack/commands`

### Jobber API Setup

1. Get API credentials from Jobber dashboard
2. Configure webhook URL: `http://localhost:5000/webhooks/jobber/webhooks`

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
- `slack_users` - Slack user data
- `slack_channels` - Slack channel data
- `slack_messages` - Message history
- `jobber_clients` - Jobber client information
- `jobber_jobs` - Job data from Jobber
- `jobber_invoices` - Invoice information

## 🔐 Security

- Environment variables for secrets
- Slack signature verification
- Non-root Docker users
- CORS configuration
- Session management with Redis

## 📝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 🐛 Troubleshooting

### Common Issues

1. **Port conflicts**: Ensure ports 3000, 5000, 5432, 6379 are available
2. **Database connection**: Check PostgreSQL is running and credentials are correct
3. **Slack webhooks**: Ensure your app is accessible from the internet for webhooks

### Health Checks

```bash
# Check backend health
curl http://localhost:5000/health

# Check frontend health
curl http://localhost/health

# Check database
docker-compose exec postgres pg_isready

# Check Redis
docker-compose exec redis redis-cli ping
```

## 📄 License

This project is licensed under the MIT License.