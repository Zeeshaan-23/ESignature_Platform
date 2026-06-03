// src/pages/AuditTrailPage.jsx

import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { getAuditTrail, getPackage, downloadAuditCSV, downloadAuditJSON } from '../api/packages';

const EVENT_LABELS = {
  'document.uploaded': {label: 'Document Uploaded', color: '#0891b2'},
  'package.created':   { label: 'Package Created',    color: '#0891b2'},
  'package.sent':      { label: 'Package Sent',       color: '#2563eb' },
  'signing.viewed':    { label: 'Document Viewed',    color: '#d97706' },
  'signing.signed':    { label: 'Document Signed',    color: '#16a34a' },
  'package.completed': { label: 'Package Completed',  color: '#7c3aed' },
  'package.expired':   { label: 'Package Expired',    color: '#dc2626' },
  'package.declined':  { label: 'Package Declined',   color: '#dc2626' },
};

export default function AuditTrailPage() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [events, setEvents] = useState([]);
  const [pkg, setPkg] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Generic blob download helper
  const triggerDownload = async (apiFn, filename) => {
    try {
      const res = await apiFn(id);
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch {
      toast.error('Export failed. Please try again.');
    }
  };

  useEffect(() => {
    Promise.all([getAuditTrail(id), getPackage(id)])
      .then(([auditRes, pkgRes]) => {
        setEvents(auditRes.data.results);
        setPkg(pkgRes.data);
      })
      .catch(() => setError('Failed to load audit trail.'))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div style={styles.center}><p>Loading...</p></div>;
  if (error) return <div style={styles.center}><p style={{color:'red'}}>{error}</p></div>;

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <button onClick={() => navigate(`/packages/${id}`)} style={styles.backBtn}>
          ← Back to Package
        </button>
        <div style={{ flex: 1 }}>
          <h2 style={styles.title}>Audit Trail</h2>
          <p style={styles.subtitle}>{pkg?.subject}</p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            onClick={() => triggerDownload(downloadAuditCSV, `audit_${id}.csv`)}
            style={styles.exportBtn}
          >
            ⬇ CSV
          </button>
          <button
            onClick={() => triggerDownload(downloadAuditJSON, `audit_${id}.json`)}
            style={styles.exportBtn}
          >
            ⬇ JSON
          </button>
        </div>
      </div>

      <div style={styles.body}>
        {/* Summary Card */}
        <div style={styles.summaryCard}>
          <div style={styles.summaryItem}>
            <span style={styles.summaryLabel}>Document</span>
            <span style={styles.summaryValue}>{pkg?.document_name}</span>
          </div>
          <div style={styles.summaryItem}>
            <span style={styles.summaryLabel}>Status</span>
            <span style={styles.summaryValue}>{pkg?.status}</span>
          </div>
          <div style={styles.summaryItem}>
            <span style={styles.summaryLabel}>Total Events</span>
            <span style={styles.summaryValue}>{events.length}</span>
          </div>
          <div style={styles.summaryItem}>
            <span style={styles.summaryLabel}>Recipients</span>
            <span style={styles.summaryValue}>{pkg?.recipients?.length}</span>
          </div>
        </div>

        {/* Timeline */}
        <div style={styles.card}>
          <h3 style={styles.cardTitle}>Event Timeline</h3>

          {events.length === 0 && (
            <p style={styles.empty}>No events recorded yet.</p>
          )}

          <div style={styles.timeline}>
            {events.map((event, index) => {
              const meta = EVENT_LABELS[event.event_type] || {
                label: event.event_type,
                color: '#6b7280'
              };

              return (
                <div key={event.id} style={styles.eventRow}>
                  {/* Timeline line */}
                  <div style={styles.timelineLeft}>
                    <div style={{
                      ...styles.dot,
                      background: meta.color
                    }} />
                    {index < events.length - 1 && (
                      <div style={styles.line} />
                    )}
                  </div>

                  {/* Event content */}
                  <div style={styles.eventContent}>
                    <div style={styles.eventHeader}>
                      <span style={{
                        ...styles.badge,
                        background: meta.color
                      }}>
                        {meta.label}
                      </span>
                      <span style={styles.timestamp}>
                        {new Date(event.created_at).toLocaleString()}
                      </span>
                    </div>

                    <div style={styles.eventDetails}>
                      {event.actor_email && (
                        <span style={styles.detail}>
                          👤 {event.actor_email}
                        </span>
                      )}
                      {event.recipient_email && (
                        <span style={styles.detail}>
                          ✉ {event.recipient_email}
                        </span>
                      )}
                      {event.ip_address && (
                        <span style={styles.detail}>
                          🌐 {event.ip_address}
                        </span>
                      )}
                      {event.metadata &&
                        Object.keys(event.metadata).length > 0 && (
                          Object.entries(event.metadata).map(([k, v]) => (
                            <span key={k} style={styles.detail}>
                              {k}: {v}
                            </span>
                          ))
                        )
                      }
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

const styles = {
  center: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  container: { minHeight: '100vh', background: '#f5f5f5' },
  header: {
    background: 'white',
    padding: '1.25rem 2rem',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
    display: 'flex',
    alignItems: 'center',
    gap: '1.5rem',
  },
  backBtn: {
    padding: '0.4rem 0.8rem',
    background: 'transparent',
    border: '1px solid #ddd',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '0.9rem',
    whiteSpace: 'nowrap',
  },
  exportBtn: {
    padding: '0.4rem 0.8rem',
    background: '#f3f4f6',
    border: '1px solid #ddd',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '0.85rem',
    whiteSpace: 'nowrap',
  },
  title: { margin: 0, marginBottom: '0.2rem' },
  subtitle: { margin: 0, color: '#666', fontSize: '0.9rem' },
  body: {
    maxWidth: '800px',
    margin: '2rem auto',
    padding: '0 1rem',
  },
  summaryCard: {
    background: 'white',
    borderRadius: '8px',
    padding: '1.25rem 1.5rem',
    marginBottom: '1.5rem',
    boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: '1rem',
  },
  summaryItem: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.25rem',
  },
  summaryLabel: { fontSize: '0.75rem', color: '#6b7280', textTransform: 'uppercase' },
  summaryValue: { fontSize: '0.95rem', fontWeight: '600' },
  card: {
    background: 'white',
    borderRadius: '8px',
    padding: '1.5rem',
    boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
  },
  cardTitle: { margin: '0 0 1.5rem', fontSize: '1rem' },
  empty: { color: '#999', textAlign: 'center', padding: '2rem 0' },
  timeline: { display: 'flex', flexDirection: 'column' },
  eventRow: {
    display: 'flex',
    gap: '1rem',
    position: 'relative',
  },
  timelineLeft: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    width: '16px',
    flexShrink: 0,
  },
  dot: {
    width: '14px',
    height: '14px',
    borderRadius: '50%',
    marginTop: '4px',
    flexShrink: 0,
    zIndex: 1,
  },
  line: {
    width: '2px',
    flex: 1,
    background: '#e5e7eb',
    minHeight: '24px',
    margin: '2px 0',
  },
  eventContent: {
    flex: 1,
    paddingBottom: '1.5rem',
  },
  eventHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
    flexWrap: 'wrap',
    marginBottom: '0.4rem',
  },
  badge: {
    padding: '0.2rem 0.6rem',
    borderRadius: '999px',
    color: 'white',
    fontSize: '0.78rem',
    fontWeight: '600',
  },
  timestamp: { color: '#6b7280', fontSize: '0.82rem' },
  eventDetails: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '0.5rem',
  },
  detail: {
    background: '#f3f4f6',
    padding: '0.2rem 0.6rem',
    borderRadius: '4px',
    fontSize: '0.8rem',
    color: '#374151',
  },
};