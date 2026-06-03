import React, { useState, useRef, useEffect } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import Draggable from 'react-draggable';
import { toast } from 'react-toastify';
import { createSignatureField, sendPackage } from '../api/packages';
import { useNavigate } from 'react-router-dom';

// Ensure the worker is loaded
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

export default function PlaceFieldsUI({ packageId, documentUrl, recipients, onComplete }) {
  const [numPages, setNumPages] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [fields, setFields] = useState([]);
  const [loading, setLoading] = useState(false);
  const pageRef = useRef(null);

  // We only care about signers (approvers and CCs don't need signature fields)
  const signers = recipients.filter((r) => r.role === 'SIGNER');

  const onDocumentLoadSuccess = ({ numPages }) => {
    setNumPages(numPages);
  };

  const addField = (signer) => {
    // Default size and position
    const newField = {
      id: Date.now(),
      recipientId: signer.id,
      recipientName: signer.name,
      page_number: currentPage,
      x: 10, // 10%
      y: 10, // 10%
      width: 25, // 25%
      height: 10, // 10%
    };
    setFields([...fields, newField]);
  };

  const updateFieldPosition = (id, e, data) => {
    if (!pageRef.current) return;
    const { offsetWidth, offsetHeight } = pageRef.current;
    
    // Calculate new percentages
    const x = (data.x / offsetWidth) * 100;
    const y = (data.y / offsetHeight) * 100;

    setFields(fields.map(f => f.id === id ? { ...f, x, y } : f));
  };

  const removeField = (id) => {
    setFields(fields.filter(f => f.id !== id));
  };

  const [showPreflight, setShowPreflight] = useState(false);

  const confirmSend = async () => {
    setShowPreflight(false);
    setLoading(true);
    try {
      // 1. Save all fields
      for (const field of fields) {
        await createSignatureField(packageId, {
          recipient: field.recipientId,
          page_number: field.page_number,
          x: field.x / 100, // convert percentage back to 0.0-1.0
          y: field.y / 100,
          width: field.width / 100,
          height: field.height / 100,
        });
      }

      // 2. Send package
      await sendPackage(packageId);
      toast.success('Package sent successfully!');
      if (onComplete) onComplete();
    } catch (err) {
      toast.error('Failed to save fields or send package.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveAndSend = () => {
    setShowPreflight(true);
  };

  const currentPageFields = fields.filter(f => f.page_number === currentPage);

  if (signers.length === 0) {
    return (
      <div style={styles.container}>
        <p>No signers added. You can just send the package.</p>
        <button onClick={confirmSend} disabled={loading} style={styles.btn}>
          {loading ? 'Sending...' : 'Send Package'}
        </button>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.sidebar}>
        <h3>Place Signatures</h3>
        <p style={{ fontSize: '0.9rem', color: '#666' }}>
          Select a signer and place their signature field on the document.
        </p>

        <div style={styles.signerList}>
          {signers.map(signer => (
            <button
              key={signer.id}
              onClick={() => addField(signer)}
              style={styles.signerBtn}
            >
              + Add field for {signer.name}
            </button>
          ))}
        </div>

        <div style={styles.pageControls}>
          <button
            disabled={currentPage <= 1}
            onClick={() => setCurrentPage(c => c - 1)}
            style={styles.pageBtn}
          >
            Prev
          </button>
          <span>Page {currentPage} of {numPages || '--'}</span>
          <button
            disabled={currentPage >= (numPages || 1)}
            onClick={() => setCurrentPage(c => c + 1)}
            style={styles.pageBtn}
          >
            Next
          </button>
        </div>

        <button 
          onClick={handleSaveAndSend} 
          disabled={loading} 
          style={styles.sendBtn}
        >
          {loading ? 'Sending...' : 'Review & Send'}
        </button>

        {showPreflight && (
          <div style={styles.modalOverlay}>
            <div style={styles.modalContent}>
              <h3>Preflight Checklist</h3>
              <ul style={styles.checklist}>
                <li>
                  {fields.length > 0 ? '✅' : '⚠️'} You have placed {fields.length} signature field(s).
                </li>
                {signers.map(signer => {
                  const hasField = fields.some(f => f.recipientId === signer.id);
                  return (
                    <li key={signer.id} style={{ marginLeft: '1.5rem', color: hasField ? '#16a34a' : '#dc2626' }}>
                      {hasField ? '✓' : '✗'} {signer.name} has {hasField ? 'a' : 'NO'} signature field assigned.
                    </li>
                  );
                })}
              </ul>
              <p style={{ fontSize: '0.9rem', color: '#666', marginTop: '1rem' }}>
                Are you ready to finalize and send this package? Once sent, it cannot be edited.
              </p>
              <div style={styles.modalActions}>
                <button onClick={() => setShowPreflight(false)} style={styles.cancelModalBtn}>Back to Editing</button>
                <button onClick={confirmSend} style={styles.confirmModalBtn}>Confirm & Send</button>
              </div>
            </div>
          </div>
        )}
      </div>

      <div style={styles.pdfContainer}>
        <Document
          file={documentUrl}
          onLoadSuccess={onDocumentLoadSuccess}
          loading="Loading PDF..."
        >
          <div ref={pageRef} style={styles.pageWrapper}>
            <Page
              pageNumber={currentPage}
              renderTextLayer={false}
              renderAnnotationLayer={false}
              width={600}
            />

            {/* Render Draggable Fields for Current Page */}
            {currentPageFields.map(field => {
              // Convert percentage to pixels for rendering
              const pageW = pageRef.current?.offsetWidth || 600;
              const pageH = pageRef.current?.offsetHeight || 848; // Approx A4 height at 600px width
              const pxX = (field.x / 100) * pageW;
              const pxY = (field.y / 100) * pageH;
              const pxW = (field.width / 100) * pageW;
              const pxH = (field.height / 100) * pageH;

              return (
                <Draggable
                  key={field.id}
                  bounds="parent"
                  position={{ x: pxX, y: pxY }}
                  onStop={(e, data) => updateFieldPosition(field.id, e, data)}
                >
                  <div style={{
                    ...styles.fieldBox,
                    width: pxW,
                    height: pxH,
                  }}>
                    <div style={styles.fieldHeader}>
                      <span style={styles.fieldName}>{field.recipientName}</span>
                      <button 
                        onClick={() => removeField(field.id)}
                        style={styles.removeBtn}
                        onPointerDown={(e) => e.stopPropagation()} // Prevent dragging when clicking remove
                      >✕</button>
                    </div>
                  </div>
                </Draggable>
              );
            })}
          </div>
        </Document>
      </div>
    </div>
  );
}

const styles = {
  container: {
    display: 'flex',
    gap: '2rem',
    background: '#f9fafb',
    padding: '2rem',
    borderRadius: '8px',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
  },
  sidebar: {
    width: '300px',
    display: 'flex',
    flexDirection: 'column',
    gap: '1.5rem',
  },
  signerList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.5rem',
  },
  signerBtn: {
    padding: '0.75rem',
    background: '#e0e7ff',
    color: '#3730a3',
    border: '1px solid #c7d2fe',
    borderRadius: '4px',
    cursor: 'pointer',
    textAlign: 'left',
    fontWeight: '500'
  },
  pageControls: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    background: 'white',
    padding: '0.75rem',
    borderRadius: '4px',
    border: '1px solid #ddd'
  },
  pageBtn: {
    padding: '0.4rem 0.8rem',
    background: '#f3f4f6',
    border: '1px solid #d1d5db',
    borderRadius: '4px',
    cursor: 'pointer'
  },
  sendBtn: {
    marginTop: 'auto',
    padding: '1rem',
    background: '#2563eb',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontWeight: 'bold',
    fontSize: '1rem'
  },
  pdfContainer: {
    flex: 1,
    overflow: 'auto',
    background: '#e5e7eb',
    padding: '1rem',
    borderRadius: '4px',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'flex-start'
  },
  pageWrapper: {
    position: 'relative',
    display: 'inline-block',
    boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
  },
  fieldBox: {
    position: 'absolute',
    background: 'rgba(59, 130, 246, 0.2)', // Blue tint
    border: '2px solid #2563eb',
    cursor: 'move',
    display: 'flex',
    flexDirection: 'column',
    boxSizing: 'border-box',
    zIndex: 10,
  },
  fieldHeader: {
    background: '#2563eb',
    color: 'white',
    fontSize: '0.75rem',
    padding: '2px 4px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center'
  },
  fieldName: {
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
  removeBtn: {
    background: 'transparent',
    border: 'none',
    color: 'white',
    cursor: 'pointer',
    padding: '0',
    marginLeft: '4px',
    fontSize: '0.8rem'
  },
  modalOverlay: {
    position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
    background: 'rgba(0,0,0,0.5)', zIndex: 100,
    display: 'flex', justifyContent: 'center', alignItems: 'center'
  },
  modalContent: {
    background: 'white', padding: '2rem', borderRadius: '8px',
    maxWidth: '500px', width: '100%', boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
  },
  checklist: {
    listStyle: 'none', padding: 0, margin: '1rem 0',
    display: 'flex', flexDirection: 'column', gap: '0.5rem'
  },
  modalActions: {
    display: 'flex', gap: '1rem', marginTop: '1.5rem', justifyContent: 'flex-end'
  },
  cancelModalBtn: {
    padding: '0.6rem 1rem', background: 'transparent', border: '1px solid #ccc',
    borderRadius: '4px', cursor: 'pointer'
  },
  confirmModalBtn: {
    padding: '0.6rem 1rem', background: '#2563eb', color: 'white',
    border: 'none', borderRadius: '4px', cursor: 'pointer'
  }
};
