// src/pages/CreatePackagePage.jsx

import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { createPackage, sendPackage } from '../api/packages';

export default function CreatePackagePage() {
  const [searchParams] = useSearchParams();
  const documentId = searchParams.get('documentId');
  const documentName = searchParams.get('documentName');

  const [subject, setSubject] = useState('');
  const [message, setMessage] = useState('');
  const [routingMode, setRoutingMode] = useState('SERIAL');
  const [recipients, setRecipients] = useState([
    { name: '', email: '', role: 'SIGNER', signing_order: 1 },
  ]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const addRecipient = () => {
    setRecipients([
      ...recipients,
      { name: '', email: '', role: 'SIGNER', signing_order: recipients.length + 1 },
    ]);
  };

  const updateRecipient = (index, field, value) => {
    const updated = [...recipients];
    updated[index][field] = value;
    setRecipients(updated);
  };

  const removeRecipient = (index) => {
    if (recipients.length === 1) return;
    setRecipients(recipients.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const res = await createPackage({
        subject,
        message,
        document: documentId,
        routing_mode: routingMode,
        recipients,
      });

      const packageId = res.data.id;

      // Send immediately after creating
      await sendPackage(packageId);
      navigate(`/packages/${packageId}`);
    } catch (err) {
      const data = err.response?.data;
      setError(
        typeof data === 'object'
          ? JSON.stringify(data)
          : 'Failed to create package.'
      );
    } finally {
      setLoading(false);
    }
  };

  if (!documentId) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <p>No document selected.</p>
        <button onClick={() => navigate('/upload')}>Upload a Document</button>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h2 style={styles.title}>Create Signing Package</h2>
        <p style={styles.docName}>📄 {documentName}</p>

        {error && <p style={styles.error}>{error}</p>}

        <form onSubmit={handleSubmit}>
          <div style={styles.field}>
            <label>Subject *</label>
            <input
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              required
              placeholder="Please sign this contract"
              style={styles.input}
            />
          </div>

          <div style={styles.field}>
            <label>Message</label>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Hi, please review and sign the attached document."
              style={styles.textarea}
            />
          </div>

          <div style={styles.field}>
            <label>Routing Mode</label>
            <select
              value={routingMode}
              onChange={(e) => setRoutingMode(e.target.value)}
              style={styles.input}
            >
              <option value="SERIAL">Serial (one at a time)</option>
              <option value="PARALLEL">Parallel (all at once)</option>
            </select>
          </div>

          <div style={styles.recipientsSection}>
            <div style={styles.recipientsHeader}>
              <label>Recipients *</label>
              <button
                type="button"
                onClick={addRecipient}
                style={styles.addBtn}
              >
                + Add Recipient
              </button>
            </div>

            {recipients.map((recipient, index) => (
              <div key={index} style={styles.recipientRow}>
                <input
                  placeholder="Full Name"
                  value={recipient.name}
                  onChange={(e) => updateRecipient(index, 'name', e.target.value)}
                  required
                  style={styles.recipientInput}
                />
                <input
                  placeholder="Email"
                  type="email"
                  value={recipient.email}
                  onChange={(e) => updateRecipient(index, 'email', e.target.value)}
                  required
                  style={styles.recipientInput}
                />
                <select
                  value={recipient.role}
                  onChange={(e) => updateRecipient(index, 'role', e.target.value)}
                  style={styles.roleSelect}
                >
                  <option value="SIGNER">Signer</option>
                  <option value="APPROVER">Approver</option>
                  <option value="CC">CC</option>
                </select>
                {recipients.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removeRecipient(index)}
                    style={styles.removeBtn}
                  >
                    ✕
                  </button>
                )}
              </div>
            ))}
          </div>

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
              disabled={loading}
              style={styles.submitBtn}
            >
              {loading ? 'Sending...' : 'Create & Send Package'}
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
    background: '#f5f5f5',
    padding: '2rem 1rem',
  },
  card: {
    background: 'white',
    padding: '2rem',
    borderRadius: '8px',
    boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
    maxWidth: '600px',
    margin: '0 auto',
  },
  title: { marginBottom: '0.5rem' },
  docName: { color: '#2563eb', marginBottom: '1.5rem', fontSize: '0.9rem' },
  error: { color: 'red', marginBottom: '1rem', fontSize: '0.9rem' },
  field: { marginBottom: '1.25rem' },
  input: {
    width: '100%',
    padding: '0.6rem',
    marginTop: '0.3rem',
    border: '1px solid #ddd',
    borderRadius: '4px',
    fontSize: '1rem',
  },
  textarea: {
    width: '100%',
    padding: '0.6rem',
    marginTop: '0.3rem',
    border: '1px solid #ddd',
    borderRadius: '4px',
    fontSize: '1rem',
    minHeight: '80px',
    resize: 'vertical',
  },
  recipientsSection: { marginBottom: '1.5rem' },
  recipientsHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '0.75rem',
  },
  addBtn: {
    padding: '0.3rem 0.75rem',
    background: 'transparent',
    border: '1px solid #2563eb',
    color: '#2563eb',
    borderRadius: '4px',
    cursor: 'pointer',
  },
  recipientRow: {
    display: 'flex',
    gap: '0.5rem',
    marginBottom: '0.5rem',
    alignItems: 'center',
  },
  recipientInput: {
    flex: 1,
    padding: '0.6rem',
    border: '1px solid #ddd',
    borderRadius: '4px',
    fontSize: '0.9rem',
  },
  roleSelect: {
    padding: '0.6rem',
    border: '1px solid #ddd',
    borderRadius: '4px',
    fontSize: '0.9rem',
  },
  removeBtn: {
    padding: '0.4rem 0.6rem',
    background: 'transparent',
    border: '1px solid #ddd',
    borderRadius: '4px',
    cursor: 'pointer',
    color: '#dc2626',
  },
  actions: { display: 'flex', gap: '1rem', marginTop: '1rem' },
  cancelBtn: {
    flex: 1,
    padding: '0.75rem',
    background: 'transparent',
    border: '1px solid #ddd',
    borderRadius: '4px',
    cursor: 'pointer',
  },
  submitBtn: {
    flex: 2,
    padding: '0.75rem',
    background: '#2563eb',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '1rem',
  },
};