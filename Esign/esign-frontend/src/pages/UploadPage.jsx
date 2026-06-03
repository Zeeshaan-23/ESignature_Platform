// src/pages/UploadPage.jsx

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { uploadDocument } from '../api/documents';

export default function UploadPage() {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) return;

    setUploading(true);
    setUploadProgress(0);
    setError('');

    try {
      const res = await uploadDocument(file, (progressEvent) => {
        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        setUploadProgress(percentCompleted);
      });
      toast.success('Document uploaded successfully!');
      // After upload, go straight to create package with document ID
      navigate(`/packages/new?documentId=${res.data.id}&documentName=${encodeURIComponent(res.data.original_filename)}`);
    } catch (err) {
      const msg = 'Upload failed. Make sure the file is a PDF or DOCX under 10MB.';
      setError(msg);
      toast.error(msg);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h2 style={styles.title}>Upload Document</h2>
        <p style={styles.subtitle}>Upload the document you want to send for signing.</p>

        {error && <p style={styles.error}>{error}</p>}

        <form onSubmit={handleUpload}>
          <div style={styles.dropzone}>
            <input
              type="file"
              accept=".pdf,.docx"
              onChange={(e) => setFile(e.target.files[0])}
              style={styles.fileInput}
            />
            {file ? (
              <p style={styles.fileName}>📄 {file.name}</p>
            ) : (
              <p style={styles.dropText}>Click to select a PDF or DOCX file</p>
            )}
          </div>

          {uploading && (
            <div style={styles.progressContainer}>
              <div style={{ ...styles.progressBar, width: `${uploadProgress}%` }}></div>
              <p style={styles.progressText}>{uploadProgress}% Uploaded</p>
            </div>
          )}

          <div style={styles.actions}>
            <button
              type="button"
              onClick={() => navigate('/')}
              style={styles.cancelBtn}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!file || uploading}
              style={styles.uploadBtn}
            >
              {uploading ? 'Uploading...' : 'Upload & Continue'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

const styles = {
  container: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: '#f5f5f5',
  },
  card: {
    background: 'white',
    padding: '2rem',
    borderRadius: '8px',
    boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
    width: '100%',
    maxWidth: '480px',
  },
  title: { marginBottom: '0.5rem' },
  subtitle: { color: '#666', marginBottom: '1.5rem', fontSize: '0.9rem' },
  error: { color: 'red', marginBottom: '1rem', fontSize: '0.9rem' },
  dropzone: {
    border: '2px dashed #ddd',
    borderRadius: '8px',
    padding: '2rem',
    textAlign: 'center',
    cursor: 'pointer',
    marginBottom: '1.5rem',
  },
  fileInput: { width: '100%', cursor: 'pointer' },
  fileName: { color: '#2563eb', fontWeight: '500' },
  dropText: { color: '#999' },
  actions: { display: 'flex', gap: '1rem' },
  cancelBtn: {
    flex: 1,
    padding: '0.75rem',
    background: 'transparent',
    border: '1px solid #ddd',
    borderRadius: '4px',
    cursor: 'pointer',
  },
  uploadBtn: {
    flex: 2,
    padding: '0.75rem',
    background: '#2563eb',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '1rem',
  },
  progressContainer: {
    marginBottom: '1.5rem',
    background: '#e5e7eb',
    borderRadius: '999px',
    overflow: 'hidden',
    height: '1.2rem',
    position: 'relative',
  },
  progressBar: {
    background: '#2563eb',
    height: '100%',
    transition: 'width 0.2s',
  },
  progressText: {
    position: 'absolute',
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
    color: 'white',
    fontSize: '0.75rem',
    fontWeight: 'bold',
    mixBlendMode: 'difference',
  }
};