# eSign Platform - Backend

The core API and backend worker service for the eSign Platform. Built with Django and Django REST Framework, it handles document processing, signature stamping, advanced workflows, and webhook deliveries.

## Tech Stack
- **Framework**: Django 6.0 + Django REST Framework (DRF)
- **Database**: PostgreSQL
- **Task Queue**: Celery + Redis
- **Authentication**: JWT (JSON Web Tokens)
- **PDF Processing**: `pypdf`, `reportlab`, `Pillow`
- **Document Processing**: `python-docx` for automatic DOCX to PDF conversion
- **Testing**: `pytest` + `pytest-django`

## Features
- **Document Pipeline**:
  - Secure uploads with size and MIME validation.
  - Automatic `.docx` to `.pdf` conversion.
  - SHA-256 hash generation on upload and post-sign tamper verification.
  - Reusable Document Templates with versioning and locking.
- **Advanced Workflows**:
  - Hybrid Routing: Mix serial and parallel signing orders.
  - Role-based Actions: Signers vs. Approvers (view-only).
  - Workflow Actions: Delegate, Return for Rework, Decline, and Resend.
  - Drag and drop coordinate recording (percentage-based) for precise signature placement on PDFs.
- **Asynchronous Tasks (Celery)**:
  - Reliable email delivery with exponential backoff for invitations, completion notices, and password resets.
  - Automatic PDF generation: Stamps signatures on coordinates and appends a "Certificate of Completion" page.
- **Audit & Compliance**:
  - Immutable Audit Log tracking over 14 discrete events across packages and users.
- **Webhooks**:
  - Outgoing webhooks with HMAC SHA-256 signature payloads.
  - Delivery retry mechanics (up to 5 attempts with backoff) to external HTTP endpoints.

## Getting Started

### Prerequisites
- Python 3.14+
- PostgreSQL
- Redis Server (for Celery)

### Installation
1. Clone the repository and navigate to the backend directory:
   ```bash
   cd esign-platform
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Configuration
Create a `.env` file in the `esign-platform/config` directory (or export variables in your environment):
```env
DEBUG=True
SECRET_KEY=your-secret-key
DATABASE_URL=postgres://user:pass@localhost:5432/esign_db
REDIS_URL=redis://127.0.0.1:6379/0

# Email Configuration (e.g. Mailtrap for dev)
EMAIL_HOST=smtp.mailtrap.io
EMAIL_PORT=2525
EMAIL_HOST_USER=your_user
EMAIL_HOST_PASSWORD=your_password
DEFAULT_FROM_EMAIL=noreply@esign.local

# Frontend URL for emails
FRONTEND_URL=http://localhost:5173
```

### Running Locally
1. Run database migrations:
   ```bash
   python manage.py migrate
   ```
2. Start the Django development server:
   ```bash
   python manage.py runserver
   ```
3. Start the Celery worker (in a separate terminal):
   ```bash
   celery -A config worker -l info
   ```

### Testing
To run the automated test suite (`pytest`):
```bash
pytest
```
*Note: Make sure your PostgreSQL user has the `CREATEDB` privilege to allow pytest to create a test database.*
