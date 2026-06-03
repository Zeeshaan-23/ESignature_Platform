// src/pages/SigningPage.jsx

import { useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Document, Page, pdfjs } from 'react-pdf';
import { getSigningLink, submitSignature, declineSignature, returnPackage, delegateSignature } from '../api/signing';
import { toast } from 'react-toastify';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';

pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

export default function SigningPage() {
  const { token } = useParams();

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [completed, setCompleted] = useState(false);
  const [completionMessage, setCompletionMessage] = useState('Your action has been recorded.');

  const [numPages, setNumPages] = useState(null);
  const [pdfError, setPdfError] = useState(false);

  // Canvas
  const canvasRef = useRef(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [hasSigned, setHasSigned] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Modals state
  const [showDeclineModal, setShowDeclineModal] = useState(false);
  const [declineReason, setDeclineReason] = useState('');
  
  const [showReturnModal, setShowReturnModal] = useState(false);
  const [returnReason, setReturnReason] = useState('');
  
  const [showDelegateModal, setShowDelegateModal] = useState(false);
  const [delegateName, setDelegateName] = useState('');
  const [delegateEmail, setDelegateEmail] = useState('');

  useEffect(() => {
    getSigningLink(token)
      .then((res) => setData(res.data))
      .catch((err) => {
        setError(err.response?.data?.error || 'Invalid or expired signing link.');
      })
      .finally(() => setLoading(false));
  }, [token]);

  // Drawing handlers
  const startDrawing = (e) => {
    const canvas = canvasRef.current;
    if(!canvas) return;
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

  const startDrawingTouch = (e) => {
    e.preventDefault();
    const touch = e.touches[0];
    const canvas = canvasRef.current;
    if(!canvas) return;
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
    if(canvas) {
      const ctx = canvas.getContext('2d');
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
    setHasSigned(false);
  };

  // Submit handlers
  const handleSubmitSignature = async () => {
    if (data?.recipient?.role === 'SIGNER' && !hasSigned) {
      toast.error('Please provide a signature.');
      return;
    }
    const signatureData = data?.recipient?.role === 'SIGNER' ? canvasRef.current.toDataURL('image/png') : null;

    try {
      setSubmitting(true);
      await submitSignature(token, signatureData);
      setCompleted(true);
      setCompletionMessage(data?.recipient?.role === 'SIGNER' ? 'Signature submitted successfully!' : 'Document approved successfully!');
      toast.success('Action completed.');
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to submit action.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDecline = async () => {
    try {
      setSubmitting(true);
      await declineSignature(token, declineReason);
      setCompleted(true);
      setCompletionMessage('You have declined the document.');
      setShowDeclineModal(false);
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to decline.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleReturn = async () => {
    if(!returnReason) return toast.error("Reason is required");
    try {
      setSubmitting(true);
      await returnPackage(token, returnReason);
      setCompleted(true);
      setCompletionMessage('Document returned for rework.');
      setShowReturnModal(false);
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to return.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelegate = async () => {
    if(!delegateName || !delegateEmail) return toast.error("Name and Email are required");
    try {
      setSubmitting(true);
      await delegateSignature(token, delegateName, delegateEmail);
      setCompleted(true);
      setCompletionMessage(`Signing right delegated to ${delegateName}.`);
      setShowDelegateModal(false);
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to delegate.');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <div style={styles.center}><p>Loading...</p></div>;
  if (error) return <div style={styles.center}><p style={{ color: 'red', fontWeight: 'bold' }}>{error}</p></div>;

  if (completed) {
    return (
      <div style={styles.center}>
        <div style={styles.card}>
          <div style={styles.successIcon}>✓</div>
          <h2>Done</h2>
          <p style={{ color: '#666', marginTop: '0.5rem' }}>{completionMessage}</p>
        </div>
      </div>
    );
  }

  const role = data?.recipient?.role;
  const signatureFields = data?.signature_fields || [];
  const requiresFieldPlacement = data?.requires_field_placement;

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h2 style={styles.headerTitle}>{data.package?.subject}</h2>
        <p style={styles.headerSub}>
          Action required: <strong>{role}</strong> | {data.recipient?.name} ({data.recipient?.email})
        </p>
        <div style={styles.headerActions}>
          {role === 'SIGNER' && (
            <button style={styles.secondaryBtn} onClick={() => setShowDelegateModal(true)}>Delegate</button>
          )}
          {role === 'APPROVER' && (
            <button style={styles.secondaryBtn} onClick={() => setShowReturnModal(true)}>Return for Rework</button>
          )}
          <button style={styles.dangerBtn} onClick={() => setShowDeclineModal(true)}>Decline</button>
        </div>
      </div>

      <div style={styles.body}>
        <div style={styles.section}>
          <h3 style={styles.sectionTitle}>Document</h3>
          <div style={styles.pdfContainer}>
            {pdfError ? (
              <div style={styles.pdfFallback}>
                <p>Unable to preview this document type.</p>
                <a href={data.document?.file_url} target="_blank" rel="noreferrer" style={styles.downloadLink}>Download to view →</a>
              </div>
            ) : (
              <Document
                file={data.document?.file_url}
                onLoadSuccess={({ numPages }) => setNumPages(numPages)}
                onLoadError={() => setPdfError(true)}
                loading={<p style={{ padding: '1rem' }}>Loading document...</p>}
              >
                {Array.from({ length: numPages || 0 }, (_, i) => {
                  const pageFields = signatureFields.filter(f => f.page_number === (i + 1));
                  return (
                    <div key={i + 1} style={{ position: 'relative', marginBottom: '1rem' }}>
                      <Page
                        pageNumber={i + 1}
                        width={Math.min(window.innerWidth - 64, 750)}
                        renderTextLayer={true}
                        renderAnnotationLayer={false}
                        inputRef={(ref) => {
                          if (ref) {
                            ref.style.position = 'relative';
                            pageFields.forEach(f => {
                              // Render an overlay box for each field
                              let el = document.getElementById(`field-${f.id}`);
                              if (!el) {
                                el = document.createElement('div');
                                el.id = `field-${f.id}`;
                                el.style.position = 'absolute';
                                el.style.backgroundColor = hasSigned ? 'rgba(34, 197, 94, 0.2)' : 'rgba(250, 204, 21, 0.4)';
                                el.style.border = hasSigned ? '2px solid #22c55e' : '2px dashed #eab308';
                                el.style.display = 'flex';
                                el.style.alignItems = 'center';
                                el.style.justifyContent = 'center';
                                el.style.fontSize = '0.75rem';
                                el.style.fontWeight = 'bold';
                                el.style.color = hasSigned ? '#16a34a' : '#ca8a04';
                                el.innerText = hasSigned ? 'Signed' : 'Sign Here';
                                ref.appendChild(el);
                              }
                              // Calculate pixel dimensions
                              const w = ref.offsetWidth;
                              const h = ref.offsetHeight;
                              el.style.left = `${(f.x / 100) * w}px`;
                              el.style.top = `${(f.y / 100) * h}px`;
                              el.style.width = `${(f.width / 100) * w}px`;
                              el.style.height = `${(f.height / 100) * h}px`;
                            });
                          }
                        }}
                      />
                    </div>
                  );
                })}
              </Document>
            )}
          </div>
        </div>

        {role === 'SIGNER' ? (
          <div style={styles.section}>
            <div style={styles.signatureHeader}>
              <h3 style={styles.sectionTitle}>Your Signature</h3>
              <button onClick={clearSignature} style={styles.clearBtn}>Clear</button>
            </div>
            {requiresFieldPlacement && signatureFields.length > 0 && (
               <p style={{...styles.signatureHint, color: '#2563eb'}}>
                 Your signature below will be applied to all {signatureFields.length} marked location(s) in the document.
               </p>
            )}
            <p style={styles.signatureHint}>Draw your signature in the box below</p>
            <canvas
              ref={canvasRef}
              width={600}
              height={150}
              style={{...styles.canvas, width: '100%', maxWidth: '600px'}}
              onMouseDown={startDrawing}
              onMouseMove={draw}
              onMouseUp={stopDrawing}
              onMouseLeave={stopDrawing}
              onTouchStart={startDrawingTouch}
              onTouchMove={drawTouch}
              onTouchEnd={stopDrawing}
            />

            <button
              onClick={handleSubmitSignature}
              disabled={!hasSigned || submitting}
              style={{
                ...styles.submitBtn,
                opacity: !hasSigned || submitting ? 0.5 : 1,
                cursor: !hasSigned || submitting ? 'not-allowed' : 'pointer',
              }}
            >
              {submitting ? 'Submitting...' : 'Apply Signature & Submit'}
            </button>
          </div>
        ) : (
          <div style={styles.section}>
            <h3 style={styles.sectionTitle}>Approval</h3>
            <p style={styles.signatureHint}>Please review the document above. Once reviewed, click Approve to complete your action.</p>
            <button
              onClick={handleSubmitSignature}
              disabled={submitting}
              style={styles.submitBtn}
            >
              {submitting ? 'Submitting...' : 'Approve Document'}
            </button>
          </div>
        )}
      </div>

      {/* Modals */}
      {showDeclineModal && (
        <div style={styles.modalOverlay}>
          <div style={styles.modalCard}>
            <h3>Decline Signing</h3>
            <p>Are you sure you want to decline? You can provide an optional reason.</p>
            <textarea value={declineReason} onChange={e => setDeclineReason(e.target.value)} style={styles.textarea} placeholder="Reason (optional)" />
            <div style={styles.modalActions}>
              <button style={styles.cancelBtn} onClick={() => setShowDeclineModal(false)}>Cancel</button>
              <button style={styles.dangerBtn} onClick={handleDecline} disabled={submitting}>Confirm Decline</button>
            </div>
          </div>
        </div>
      )}

      {showReturnModal && (
        <div style={styles.modalOverlay}>
          <div style={styles.modalCard}>
            <h3>Return for Rework</h3>
            <p>Return this document to the sender for changes. A reason is required.</p>
            <textarea value={returnReason} onChange={e => setReturnReason(e.target.value)} style={styles.textarea} placeholder="Explain what needs to be changed..." required />
            <div style={styles.modalActions}>
              <button style={styles.cancelBtn} onClick={() => setShowReturnModal(false)}>Cancel</button>
              <button style={styles.primaryBtn} onClick={handleReturn} disabled={submitting || !returnReason}>Return Document</button>
            </div>
          </div>
        </div>
      )}

      {showDelegateModal && (
        <div style={styles.modalOverlay}>
          <div style={styles.modalCard}>
            <h3>Delegate Signing</h3>
            <p>Assign someone else to sign this document on your behalf. Your signing link will become invalid.</p>
            <input value={delegateName} onChange={e => setDelegateName(e.target.value)} style={styles.input} placeholder="Delegate's Full Name" required />
            <input value={delegateEmail} onChange={e => setDelegateEmail(e.target.value)} style={styles.input} type="email" placeholder="Delegate's Email" required />
            <div style={styles.modalActions}>
              <button style={styles.cancelBtn} onClick={() => setShowDelegateModal(false)}>Cancel</button>
              <button style={styles.primaryBtn} onClick={handleDelegate} disabled={submitting || !delegateName || !delegateEmail}>Confirm Delegation</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const styles = {
  center: { minHeight: '100vh', display: 'flex', justifyContent: 'center', alignItems: 'center', background: '#f5f5f5' },
  card: { background: 'white', padding: '3rem 2rem', borderRadius: '8px', boxShadow: '0 2px 10px rgba(0,0,0,0.1)', textAlign: 'center', maxWidth: '400px', width: '100%' },
  successIcon: { width: '60px', height: '60px', background: '#16a34a', color: 'white', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.8rem', margin: '0 auto 1rem' },
  container: { minHeight: '100vh', background: '#f5f5f5' },
  header: { background: 'white', padding: '1.25rem 2rem', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', marginBottom: '2rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' },
  headerTitle: { margin: 0 },
  headerSub: { color: '#666', margin: 0, fontSize: '0.9rem' },
  headerActions: { display: 'flex', gap: '1rem', marginTop: '0.5rem' },
  body: { maxWidth: '800px', margin: '0 auto', padding: '0 1rem 2rem' },
  section: { background: 'white', borderRadius: '8px', padding: '1.5rem', marginBottom: '1.5rem', boxShadow: '0 1px 3px rgba(0,0,0,0.08)' },
  sectionTitle: { margin: '0 0 1rem', fontSize: '1rem', fontWeight: '600' },
  pdfContainer: { border: '1px solid #eee', borderRadius: '4px', overflow: 'auto', maxHeight: '600px', background: '#525659', display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '1rem', gap: '1rem' },
  pdfFallback: { padding: '2rem', textAlign: 'center', color: 'white' },
  downloadLink: { color: '#93c5fd', marginTop: '0.5rem', display: 'inline-block' },
  signatureHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' },
  signatureHint: { color: '#666', fontSize: '0.85rem', marginBottom: '0.75rem' },
  canvas: { border: '2px solid #ddd', borderRadius: '4px', cursor: 'crosshair', display: 'block', background: 'white', touchAction: 'none' },
  clearBtn: { padding: '0.3rem 0.75rem', background: 'transparent', border: '1px solid #ddd', borderRadius: '4px', cursor: 'pointer', fontSize: '0.85rem' },
  submitBtn: { width: '100%', padding: '0.9rem', background: '#2563eb', color: 'white', border: 'none', borderRadius: '6px', fontSize: '1rem', marginTop: '1rem' },
  secondaryBtn: { padding: '0.5rem 1rem', background: '#f3f4f6', border: '1px solid #d1d5db', borderRadius: '4px', cursor: 'pointer', fontSize: '0.85rem' },
  dangerBtn: { padding: '0.5rem 1rem', background: '#fef2f2', color: '#dc2626', border: '1px solid #fecaca', borderRadius: '4px', cursor: 'pointer', fontSize: '0.85rem' },
  primaryBtn: { padding: '0.5rem 1rem', background: '#2563eb', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '0.85rem' },
  cancelBtn: { padding: '0.5rem 1rem', background: 'transparent', border: 'none', color: '#666', cursor: 'pointer', fontSize: '0.85rem' },
  modalOverlay: { position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 100 },
  modalCard: { background: 'white', padding: '2rem', borderRadius: '8px', width: '100%', maxWidth: '400px', display: 'flex', flexDirection: 'column', gap: '1rem' },
  modalActions: { display: 'flex', justifyContent: 'flex-end', gap: '1rem', marginTop: '1rem' },
  textarea: { width: '100%', padding: '0.75rem', border: '1px solid #ddd', borderRadius: '4px', resize: 'vertical', minHeight: '80px', boxSizing: 'border-box' },
  input: { width: '100%', padding: '0.75rem', border: '1px solid #ddd', borderRadius: '4px', boxSizing: 'border-box' },
};