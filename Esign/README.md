# eSign Platform - Quick Start Guide

This guide will walk you through how to run the entire eSign platform (Frontend, Backend, Database, and Background Workers) locally on your machine so you can test all the features yourself.

## Prerequisites
Before you begin, ensure you have the following installed on your machine:
1. **Node.js** (v18+) - For the frontend
2. **Python** (3.14+) - For the backend
3. **PostgreSQL** - For the database
4. **Redis** - For the task queue (Celery)
5. **Git** - To clone/pull the repository

---

## 1. Setup the Database & Redis
1. Make sure your **PostgreSQL** server is running. Create a database named `esign_db`.
   ```sql
   CREATE DATABASE esign_db;
   CREATE USER esign_user WITH PASSWORD 'your_password';
   ALTER ROLE esign_user SET client_encoding TO 'utf8';
   ALTER ROLE esign_user SET default_transaction_isolation TO 'read committed';
   ALTER ROLE esign_user SET timezone TO 'UTC';
   GRANT ALL PRIVILEGES ON DATABASE esign_db TO esign_user;
   ALTER USER esign_user CREATEDB; -- Required for running tests
   ```
2. Make sure your **Redis** server is running. (On Windows, you can use WSL to run Redis or use a tool like Memurai).
   ```bash
   redis-server
   ```

---

## 2. Start the Backend API (Terminal 1)
Open a terminal and navigate to the backend directory:
```bash
cd esign-platform
```

1. **Activate the virtual environment**:
   ```bash
   # Windows
   venv\Scripts\activate
   # Mac/Linux
   source venv/bin/activate
   ```
2. **Install dependencies** (if you haven't already):
   ```bash
   pip install -r requirements.txt
   ```
3. **Create a `.env` file** in `esign-platform/config/.env` with the following:
   ```env
   DEBUG=True
   SECRET_KEY=your-secret-key-here
   DATABASE_URL=postgres://esign_user:your_password@localhost:5432/esign_db
   REDIS_URL=redis://127.0.0.1:6379/0
   
   # You can use Mailtrap.io for testing emails locally
   EMAIL_HOST=smtp.mailtrap.io
   EMAIL_PORT=2525
   EMAIL_HOST_USER=your_mailtrap_user
   EMAIL_HOST_PASSWORD=your_mailtrap_password
   DEFAULT_FROM_EMAIL=noreply@esign.local
   
   FRONTEND_URL=http://localhost:5173
   ```
4. **Run Migrations** (creates the database tables):
   ```bash
   python manage.py migrate
   ```
5. **Start the Django Server**:
   ```bash
   python manage.py runserver
   ```
   *The backend will be running at `http://localhost:8000/`*

---

## 3. Start the Celery Worker (Terminal 2)
The platform uses background workers to generate PDFs, send emails, and deliver webhooks asynchronously.

Open a **new terminal** and navigate to the backend directory:
```bash
cd esign-platform
venv\Scripts\activate
```
Start the worker:
```bash
# On Windows, you might need to use the 'solo' pool
celery -A config worker -l info --pool=solo
```
*You should see a message saying "celery@<your-pc> ready."*

---

## 4. Start the Frontend (Terminal 3)
Open a **third terminal** and navigate to the frontend directory:
```bash
cd esign-frontend
```

1. **Install dependencies**:
   ```bash
   npm install
   ```
2. **Create a `.env` file** in the `esign-frontend` root folder:
   ```env
   VITE_API_URL=http://127.0.0.1:8000/api
   ```
3. **Start the Vite server**:
   ```bash
   npm run dev
   ```
   *The frontend will be running at `http://localhost:5173/`*

---

## How to Test the Features

Once all 3 terminals are running (Django, Celery, and Vite), open your browser to `http://localhost:5173`.

### **1. Core Flow**
1. Click **Register** to create a new account.
2. Once logged in, click **+ New Package** or upload a `.pdf` or `.docx` file from the **Upload** page.
3. Enter a subject and add a recipient (e.g., your own alternate email) with the role **Signer**.
4. Click **Next: Place Fields**. You will see the document visually.
5. **Drag and drop** a signature field onto the document for your recipient.
6. Click **Review & Send**, check the Preflight Checklist, and click **Confirm & Send**.

### **2. Email & Signing (Background Tasks)**
1. Check your **Celery terminal** to verify the `send_signing_invitation` task fired.
2. Check your **Mailtrap inbox** (or the console if using a console email backend) for the invite link.
3. Open the link (it will look like `http://localhost:5173/sign/<token>`).
4. Click the signature field, draw your signature, and submit!

### **3. PDF Generation & Templates**
1. Once signed, check your Celery terminal again—you will see `generate_signed_pdf` run automatically, stamping your signature and generating the Certificate of Completion!
2. Go back to your Dashboard, click on **Templates**, and try saving an uploaded document as a template to bypass the upload step in the future.
