# eSign Platform - Frontend

The frontend for the eSign Platform, an open-source, scalable electronic signature solution built with React and Vite.

## Tech Stack
- **Framework**: React 18
- **Build Tool**: Vite
- **Routing**: React Router v6
- **HTTP Client**: Axios (configured with JWT interceptors)
- **PDF Rendering**: React-PDF (pdf.js)
- **Interactive UI**: React-Draggable for signature field placement
- **Charts**: Recharts for dashboard analytics
- **Notifications**: React-Toastify

## Features
- **Authentication**: JWT-based login, registration, and password reset flows.
- **Dashboard**: Real-time metrics, recent packages, and status filtering.
- **Document Pipeline**: Upload PDF and DOCX files.
- **Advanced Workflows**:
  - Drag and Drop signature field placement on PDF canvases.
  - Support for parallel and serial routing modes.
  - Approve, Return, Decline, and Delegate workflows.
- **Templates**: Save and reuse standard documents and routing configurations.
- **Webhooks UI**: Subscribe external services to package/document events via a dedicated management page.

## Getting Started

### Prerequisites
- Node.js (v18+)
- npm or yarn

### Installation
1. Clone the repository and navigate to the frontend directory:
   ```bash
   cd esign-frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```

### Configuration
Create a `.env` file in the root of the frontend directory:
```env
VITE_API_URL=http://127.0.0.1:8000/api
```

### Running Locally
Start the Vite development server:
```bash
npm run dev
```
The application will be accessible at `http://localhost:5173`.

### Build for Production
To build the static assets for production:
```bash
npm run build
```
The output will be placed in the `dist/` directory, ready to be served by Nginx or your preferred static file server.
