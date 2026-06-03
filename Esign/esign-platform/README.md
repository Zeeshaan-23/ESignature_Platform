# eSign Platform

A secure, enterprise-grade electronic signature platform built with Django and Django REST Framework.

## Overview

eSign Platform allows users to upload documents, create signing packages, send them to recipients, and collect legally-traceable electronic signatures — all through a clean REST API.

## Tech Stack

- **Backend:** Django 6.0, Django REST Framework
- **Auth:** JWT via djangorestframework-simplejwt
- **Database:** PostgreSQL (SQLite for development)
- **File Storage:** Local filesystem (S3-compatible in production)
- **Task Queue:** Celery + Redis (email notifications)
- **Python:** 3.14

## Architecture

```
esign-platform/
├── config/       # Project settings and root URL config
├── users/        # Custom user model, JWT auth API
├── documents/    # Document upload, storage, SHA-256 hashing
├── packages/     # Signing packages, recipients, routing
├── signing/      # Token-based public signing flow
├── audit/        # Immutable event audit trail
└── media/        # Uploaded files (gitignored)
```
## Features

- Custom user model with email-based authentication and role system
- Document upload with SHA-256 tamper detection
- Signing packages with serial and parallel recipient routing
- Token-based signing flow — no account required for signers
- Immutable audit trail with IP logging for every state change
- JWT authentication with access and refresh tokens

## API Endpoints

### Auth
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/users/register/` | Register new user | Public |
| POST | `/api/users/login/` | Login, get JWT tokens | Public |
| POST | `/api/users/token/refresh/` | Refresh access token | Public |
| GET | `/api/users/me/` | Get current user profile | Required |

### Documents
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/documents/upload/` | Upload PDF or DOCX | Required |
| GET | `/api/documents/` | List your documents | Required |
| GET | `/api/documents/<uuid>/` | Get document detail | Required |

### Packages
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/packages/create/` | Create signing package | Required |
| GET | `/api/packages/` | List your packages | Required |
| GET | `/api/packages/<uuid>/` | Get package detail | Required |
| POST | `/api/packages/<uuid>/send/` | Send package to recipients | Required |

### Signing (Public)
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/signing/<token>/` | Access signing link | Public |
| POST | `/api/signing/<token>/submit/` | Submit signature | Public |

### Audit
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/audit/packages/<uuid>/` | Get package audit trail | Required |

## Local Setup

### Prerequisites
- Python 3.10+
- pip
- Git

### Steps

**1. Clone the repository:**
```bash
git clone https://github.com/Zeeshaan-23/esign-platform.git
cd esign-platform
```

**2. Create and activate virtual environment:**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

**3. Install dependencies:**
```bash
pip install -r requirements.txt
```

**4. Create environment file:**
```bash
cp .env.example .env
```
Edit `.env` with your values.

**5. Run migrations:**
```bash
python manage.py migrate
```

**6. Create superuser:**
```bash
python manage.py createsuperuser
```

**7. Run the development server:**
```bash
python manage.py runserver
```

API is now available at `http://127.0.0.1:8000/`

## Environment Variables

Create a `.env` file in the project root:
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
DATABASE_URL=sqlite:///db.sqlite3

## Running the Signing Flow

1. Register and login to get a JWT token
2. Upload a document (`POST /api/documents/upload/`)
3. Create a package with recipients (`POST /api/packages/create/`)
4. Send the package (`POST /api/packages/<uuid>/send/`)
5. Access the signing link (`GET /api/signing/<token>/`)
6. Submit the signature (`POST /api/signing/<token>/submit/`)
7. View the audit trail (`GET /api/audit/packages/<uuid>/`)

## Git Workflow

This project follows Conventional Commits:

- `feat` — new feature
- `fix` — bug fix
- `chore` — setup or tooling changes
- `refactor` — code restructuring

## License

MIT
