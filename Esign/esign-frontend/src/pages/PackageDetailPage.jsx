// src/pages/PackageDetailPage.jsx

import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { toast } from 'react-toastify';
import { getPackage, cancelPackage, resendPackage } from '../api/packages';

export default function PackageDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [pkg, setPkg] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchPackage = async () => {
      try {
        const res = await getPackage(id);
        setPkg(res.data);
      } catch (err) {
        setError('Failed to load package.');
      } finally {
        setLoading(false);
      }
    };

    fetchPackage();
  }, [id]);

  if (loading) {
    return (
      <div style={styles.center}>
        <p>Loading package...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={styles.center}>
        <p style={{ color: 'red' }}>{error}</p>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <div style={styles.header}>
          <div>
            <h1 style={styles.title}>{pkg.subject}</h1>
            <p style={styles.status}>
              Status: <strong>{pkg.status}</strong>
            </p>
            {pkg.status === 'COMPLETED' && pkg.signed_file_url && (
              <a href={pkg.signed_file_url}
                target="_blank"
                rel="noreferrer"
                style={styles.downloadBtn}
              >
                ⬇ Download Signed Document
              </a>
            )}
          </div>
          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
            <button
              onClick={() => navigate(`/packages/${id}/audit`)}
              style={styles.auditBtn}
            >
              View Audit Trail
            </button>
            {pkg.status === 'RETURNED' && (
              <button
                onClick={async () => {
                  try {
                    await resendPackage(id);
                    toast.success('Package resent successfully!');
                    setPkg({ ...pkg, status: 'IN_PROGRESS' }); // Optimistic update
                  } catch {
                    toast.error('Failed to resend package.');
                  }
                }}
                style={styles.resendBtn}
              >
                Resend Package
              </button>
            )}
            {['SENT', 'IN_PROGRESS', 'DRAFT', 'RETURNED'].includes(pkg.status) && (
              <button
                onClick={async () => {
                  if (!window.confirm('Cancel this package? This cannot be undone.')) return;
                  try {
                    await cancelPackage(id);
                    toast.success('Package cancelled.');
                    setPkg({ ...pkg, status: 'CANCELLED' });
                  } catch {
                    toast.error('Failed to cancel package.');
                  }
                }}
                style={styles.cancelBtn}
              >
                Cancel Package
              </button>
            )}
          </div>
        </div>

        <div style={styles.section}>
          <h3>Package Info</h3>

          <div style={styles.infoGrid}>
            <div>
              <p style={styles.label}>Routing Mode</p>
              <p>{pkg.routing_mode}</p>
            </div>

            <div>
              <p style={styles.label}>Sender</p>
              <p>{pkg.sender_email}</p>
            </div>

            <div>
              <p style={styles.label}>Created</p>
              <p>{new Date(pkg.created_at).toLocaleString()}</p>
            </div>
          </div>
        </div>

        <div style={styles.section}>
          <h3>Recipients</h3>

          {pkg.recipients.map((recipient) => (
            <div key={recipient.id} style={styles.recipientCard}>
              <div>
                <p style={styles.recipientName}>
                  {recipient.name}
                </p>

                <p style={styles.recipientEmail}>
                  {recipient.email}
                </p>
              </div>

              <div style={styles.recipientMeta}>
                <span style={styles.badge}>
                  {recipient.role}
                </span>

                <span style={styles.statusBadge}>
                  {recipient.status}
                </span>
              </div>
            </div>
          ))}
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

  container: {
    minHeight: '100vh',
    background: '#f5f5f5',
    padding: '2rem',
  },

  card: {
    maxWidth: '900px',
    margin: '0 auto',
    background: 'white',
    borderRadius: '8px',
    padding: '2rem',
    boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
  },

  header: {
    marginBottom: '2rem',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: '1rem',
  },

  title: {
    marginBottom: '0.5rem',
  },

  status: {
    color: '#666',
  },

  section: {
    marginBottom: '2rem',
  },

  infoGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
    gap: '1rem',
  },

  label: {
    color: '#666',
    fontSize: '0.85rem',
    marginBottom: '0.25rem',
  },

  recipientCard: {
    border: '1px solid #eee',
    borderRadius: '6px',
    padding: '1rem',
    marginBottom: '1rem',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    background: '#fafafa',
  },

  recipientName: {
    fontWeight: '600',
    marginBottom: '0.25rem',
  },

  recipientEmail: {
    color: '#666',
    fontSize: '0.9rem',
  },

  recipientMeta: {
    display: 'flex',
    gap: '0.5rem',
  },

  badge: {
    background: '#dbeafe',
    color: '#1d4ed8',
    padding: '0.3rem 0.7rem',
    borderRadius: '999px',
    fontSize: '0.8rem',
    fontWeight: '500',
  },

  statusBadge: {
    background: '#dcfce7',
    color: '#166534',
    padding: '0.3rem 0.7rem',
    borderRadius: '999px',
    fontSize: '0.8rem',
    fontWeight: '500',
  },
  downloadBtn: {
    display: 'inline-block',
    marginTop: '1rem',
    padding: '0.6rem 1.2rem',
    background: '#16a34a',
    color: 'white',
    borderRadius: '4px',
    textDecoration: 'none',
    fontSize: '0.9rem',
  },
  auditBtn: {
    padding: '0.5rem 1rem',
    background: 'transparent',
    border: '1px solid #2563eb',
    color: '#2563eb',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '0.9rem',
  },
  resendBtn: {
    padding: '0.5rem 1rem',
    background: '#2563eb',
    border: '1px solid #2563eb',
    color: 'white',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '0.9rem',
  },
  cancelBtn: {
    padding: '0.5rem 1rem',
    background: 'transparent',
    border: '1px solid #dc2626',
    color: '#dc2626',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '0.9rem',
  },
};