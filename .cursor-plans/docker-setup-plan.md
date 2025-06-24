# Docker Setup Plan: Slack & Jobber Integration Application

## Project Overview
Building a dockerized application with React frontend (Vite), Flask backend, Redis, and PostgreSQL for Slack and Jobber integration with CRUD interface and webhook support.

## Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  React Frontend │    │  Flask Backend  │    │    PostgreSQL   │
│     (Vite)      │    │   (API/Webhooks)│    │    Database     │
│     Port 3000   │    │    Port 5000    │    │    Port 5432    │
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

## Implementation Plan

### Phase 1: Project Structure Setup
- [ ] Create project directory structure
- [ ] Initialize React frontend with Vite
- [ ] Set up Flask backend structure
- [ ] Create Docker configuration files
- [ ] Set up docker-compose.yml

### Phase 2: Backend Setup
- [ ] Create Flask application with factory pattern
- [ ] Set up database models for Slack/Jobber data
- [ ] Configure SQLAlchemy with PostgreSQL
- [ ] Set up Redis for session management
- [ ] Create API endpoints structure
- [ ] Add webhook endpoints for Slack/Jobber

### Phase 3: Frontend Setup
- [ ] Initialize Vite React application
- [ ] Set up routing with React Router
- [ ] Create component structure
- [ ] Set up API client (Axios/Fetch)
- [ ] Create CRUD interface components

### Phase 4: Docker Configuration
- [ ] Create Dockerfile for Flask backend
- [ ] Create Dockerfile for React frontend
- [ ] Configure docker-compose with all services
- [ ] Set up environment variables
- [ ] Configure service networking

### Phase 5: Integration Setup
- [ ] Set up Slack API integration
- [ ] Set up Jobber API integration
- [ ] Create webhook handlers
- [ ] Add authentication/authorization

## Directory Structure
```
dhyana-test/
├── .cursor-plans/
│   └── docker-setup-plan.md
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app.py
│   ├── config.py
│   ├── models/
│   ├── routes/
│   └── utils/
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.js
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── utils/
│   └── public/
├── docker-compose.yml
├── .env.example
└── README.md
```

## Technology Stack

### Backend
- **Flask**: Web framework
- **SQLAlchemy**: ORM for PostgreSQL
- **Flask-CORS**: Cross-origin resource sharing
- **Flask-RESTful**: RESTful API development
- **Redis**: Session management and caching
- **Celery**: Background task processing (for webhooks)
- **Gunicorn**: WSGI server

### Frontend
- **React**: UI framework
- **Vite**: Build tool and dev server
- **React Router**: Client-side routing
- **Axios**: HTTP client
- **Tailwind CSS**: Styling framework
- **React Hook Form**: Form management

### Infrastructure
- **PostgreSQL**: Primary database
- **Redis**: Session store and message broker
- **Docker**: Containerization
- **Docker Compose**: Multi-container orchestration

## Environment Variables
```
# Database
POSTGRES_DB=slack_jobber_app
POSTGRES_USER=app_user
POSTGRES_PASSWORD=secure_password
DATABASE_URL=postgresql://app_user:secure_password@postgres:5432/slack_jobber_app

# Redis
REDIS_URL=redis://redis:6379

# Slack
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_SIGNING_SECRET=your-signing-secret

# Jobber
JOBBER_API_KEY=your-api-key
JOBBER_API_SECRET=your-api-secret

# Flask
FLASK_ENV=production
SECRET_KEY=your-secret-key
```

## Docker Services Configuration

### Flask Backend (Port 5000)
- Python 3.11 Alpine base image
- Gunicorn WSGI server
- Connected to PostgreSQL and Redis
- Volume mount for development

### React Frontend (Port 3000)
- Node.js 18 Alpine base image
- Vite dev server (development)
- Nginx server (production)
- Proxy API requests to backend

### PostgreSQL (Port 5432)
- Official PostgreSQL 15 image
- Data persistence with named volume
- Health checks

### Redis (Port 6379)
- Official Redis 7 Alpine image
- Used for sessions and Celery broker
- Data persistence with named volume

## Development Workflow
1. Run `docker-compose up -d` to start all services
2. Backend available at `http://localhost:5000`
3. Frontend available at `http://localhost:3000`
4. PostgreSQL available at `localhost:5432`
5. Redis available at `localhost:6379`

## Production Considerations
- Use multi-stage builds for smaller images
- Implement proper logging
- Add health checks for all services
- Use secrets management
- Configure proper CORS settings
- Set up SSL/TLS termination

## Next Steps After Setup
1. Implement Slack OAuth flow
2. Set up Jobber API authentication
3. Create database migrations
4. Build CRUD interfaces
5. Implement webhook processing
6. Add comprehensive error handling
7. Set up testing framework
8. Add monitoring and logging

---

## Task Execution Checklist

### Current Phase: Phase 1 - Project Structure Setup ✅
- [x] Create project directory structure
- [x] Initialize React frontend with Vite
- [x] Set up Flask backend structure
- [x] Create Docker configuration files
- [x] Set up docker-compose.yml

### Completed Components
- [x] Flask backend with proper factory pattern
- [x] Database models for Slack and Jobber data
- [x] API routes with CRUD operations
- [x] Webhook handlers for Slack and Jobber
- [x] Authentication routes for OAuth
- [x] Docker configurations for all services
- [x] PostgreSQL and Redis setup
- [x] React frontend with Vite
- [x] Environment configuration
- [x] Comprehensive documentation

### Ready for Next Steps
The dockerized environment is now set up and ready for:
1. Testing the basic setup with `docker-compose --profile dev up -d`
2. Implementing the React frontend components
3. Adding authentication flows
4. Setting up Slack and Jobber integrations
5. Creating the CRUD interfaces