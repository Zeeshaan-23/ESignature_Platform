// src/pages/SigningPage.jsx

import { useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Document, Page, pdfjs } from 'react-pdf';
import { getSigningLink, submitSignature } from '../api/signing';
import { toast } from 'react-toastify';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';

// Required: tell react-pdf where to find the PDF worker
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).toString();

export default function SigningPage() {
  const { token } = useParams();

  // Data state
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [completed, setCompleted] = useState(false);

  // PDF state
  const [numPages, setNumPages] = useState(null);
  const [pdfError, setPdfError] = useState(false);

  // Signature canvas state
  const canvasRef = useRef(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [hasSigned, setHasSigned] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Load signing data on mount
  useEffect(() => {
    getSigningLink(token)
      .then((res) => setData(res.data))
      .catch(() => setError('Invalid or expired signing link.'))
      .finally(() => setLoading(false));
  }, [token]);

  // Canvas drawing — mouse events
  const startDrawing = (e) => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const rect = canvas.getBoundingClientRect();
    ctx.beginPath();
    ctx.moveTo(e.clientX - rect.left, e.clientY - rect.top);
    setIsDrawing(true);
  };

  const draw = (e) => {
    if (!isDrawing) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const rect = canvas.getBoundingClientRect();
    ctx.lineTo(e.clientX - rect.left, e.clientY - rect.top);
    ctx.strokeStyle = '#1a1a2e';
    ctx.lineWidth = 2;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.stroke();
    setHasSigned(true);
  };

  const stopDrawing = () => setIsDrawing(false);

  // Canvas drawing — touch events (mobile)
  const startDrawingTouch = (e) => {
    e.preventDefault();
    const touch = e.touches[0];
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const ctx = canvas.getContext('2d');
    ctx.beginPath();
    ctx.moveTo(touch.clientX - rect.left, touch.clientY - rect.top);
    setIsDrawing(true);
  };

  const drawTouch = (e) => {
    e.preventDefault();
    if (!isDrawing) return;
    const touch = e.touches[0];
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const ctx = canvas.getContext('2d');
    ctx.lineTo(touch.clientX - rect.left, touch.clientY - rect.top);
    ctx.strokeStyle = '#1a1a2e';
    ctx.lineWidth = 2;
    ctx.lineCap = 'round';
    ctx.stroke();
    setHasSigned(true);
  };

  const clearSignature = () => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    setHasSigned(false);
  };

  const handleSubmit = async () => {
    if (!hasSigned) return;

    const canvas = canvasRef.current;
    const signatureData = canvas.toDataURL('image/png');

    try {
      setSubmitting(true);
      await submitSignature(token, signatureData);
      setCompleted(true);
      toast.success('Signature submitted successfully!');
    } catch (err) {
      const msg = 'Failed to submit signature. Please try again.';
      setError(msg);
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <div style={styles.center}><p>Loading...</p></div>;
  if (error) return <div style={styles.center}><p style={{ color: 'red' }}>{error}</p></div>;

  if (completed) {
    return (
      <div style={styles.center}>
        <div style={styles.card}>
          <div style={styles.successIcon}>✓</div>
          <h2>Document Signed</h2>
          <p style={{ color: '#666', marginTop: '0.5rem' }}>
            Your signature has been submitted successfully.
          </p>
          <p style={{ color: '#666', fontSize: '0.85rem', marginTop: '0.5rem' }}>
            You will receive a copy of the signed document by email.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <h2 style={styles.headerTitle}>{data.package?.subject}</h2>
        <p style={styles.headerSub}>
          Signing as: <strong>{data.recipient?.name}</strong> ({data.recipient?.email})
        </p>
      </div>

      <div style={styles.body}>
        {/* PDF Viewer */}
        <div style={styles.section}>
          <h3 style={styles.sectionTitle}>Document</h3>
          <div style={styles.pdfContainer}>
            {pdfError ? (
              <div style={styles.pdfFallback}>
                <p>Unable to preview this document type.</p>
                
                <a href={data.document?.file_url}
                  target="_blank"
                  rel="noreferrer"
                  style={styles.downloadLink}
                >
                  Download to view →
                </a>
              </div>
            ) : (
              <Document
                file={data.document?.file_url}
                onLoadSuccess={({ numPages }) => setNumPages(numPages)}
                onLoadError={() => setPdfError(true)}
                loading={<p style={{ padding: '1rem' }}>Loading document...</p>}
              >
                {Array.from({ length: numPages || 0 }, (_, i) => (
                  <Page
                    key={i + 1}
                    pageNumber={i + 1}
                    width={Math.min(window.innerWidth - 64, 750)}
                    renderTextLayer={true}
                    renderAnnotationLayer={false}
                  />
                ))}
              </Document>
            )}
          </div>
        </div>

        {/* Signature Pad */}
        <div style={styles.section}>
          <div style={styles.signatureHeader}>
            <h3 style={styles.sectionTitle}>Your Signature</h3>
            <button onClick={clearSignature} style={styles.clearBtn}>
              Clear
            </button>
          </div>
          <p style={styles.signatureHint}>
            Draw your signature in the box below
          </p>
          <canvas
            ref={canvasRef}
            width={600}
            height={150}
            style={styles.canvas}
            onMouseDown={startDrawing}
            onMouseMove={draw}
            onMouseUp={stopDrawing}
            onMouseLeave={stopDrawing}
            onTouchStart={startDrawingTouch}
            onTouchMove={drawTouch}
            onTouchEnd={stopDrawing}
          />

          <button
            onClick={handleSubmit}
            disabled={!hasSigned || submitting}
            style={{
              ...styles.submitBtn,
              opacity: !hasSigned || submitting ? 0.5 : 1,
              cursor: !hasSigned || submitting ? 'not-allowed' : 'pointer',
            }}
          >
            {submitting ? 'Submitting...' : 'Submit Signature'}
          </button>

          {!hasSigned && (
            <p style={styles.hint}>Please draw your signature above before submitting.</p>
          )}
        </div>
      </div>
    </div>
  );
}

const styles = {
  center: {
    minHeight: '100vh',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    background: '#f5f5f5',
  },
  card: {
    background: 'white',
    padding: '3rem 2rem',
    borderRadius: '8px',
    boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
    textAlign: 'center',
    maxWidth: '400px',
    width: '100%',
  },
  successIcon: {
    width: '60px',
    height: '60px',
    background: '#16a34a',
    color: 'white',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '1.8rem',
    margin: '0 auto 1rem',
  },
  container: {
    minHeight: '100vh',
    background: '#f5f5f5',
  },
  header: {
    background: 'white',
    padding: '1.25rem 2rem',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
    marginBottom: '2rem',
  },
  headerTitle: { margin: 0, marginBottom: '0.25rem' },
  headerSub: { color: '#666', margin: 0, fontSize: '0.9rem' },
  body: {
    maxWidth: '800px',
    margin: '0 auto',
    padding: '0 1rem 2rem',
  },
  section: {
    background: 'white',
    borderRadius: '8px',
    padding: '1.5rem',
    marginBottom: '1.5rem',
    boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
  },
  sectionTitle: {
    margin: '0 0 1rem',
    fontSize: '1rem',
    fontWeight: '600',
  },
  pdfContainer: {
    border: '1px solid #eee',
    borderRadius: '4px',
    overflow: 'auto',
    maxHeight: '600px',
    background: '#525659',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    padding: '1rem',
    gap: '1rem',
  },
  pdfFallback: {
    padding: '2rem',
    textAlign: 'center',
    color: 'white',
  },
  downloadLink: {
    color: '#93c5fd',
    marginTop: '0.5rem',
    display: 'inline-block',
  },
  signatureHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '0.5rem',
  },
  signatureHint: {
    color: '#666',
    fontSize: '0.85rem',
    marginBottom: '0.75rem',
  },
  canvas: {
    border: '2px solid #ddd',
    borderRadius: '4px',
    cursor: 'crosshair',
    display: 'block',
    width: '100%',
    background: 'white',
    touchAction: 'none',
  },
  clearBtn: {
    padding: '0.3rem 0.75rem',
    background: 'transparent',
    border: '1px solid #ddd',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '0.85rem',
  },
  submitBtn: {
    width: '100%',
    padding: '0.9rem',
    background: '#2563eb',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    fontSize: '1rem',
    marginTop: '1rem',
  },
  hint: {
    color: '#999',
    fontSize: '0.8rem',
    textAlign: 'center',
    marginTop: '0.5rem',
  },
};