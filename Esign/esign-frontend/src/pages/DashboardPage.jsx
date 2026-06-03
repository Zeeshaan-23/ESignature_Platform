// src/pages/DashboardPage.jsx

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { listPackages } from '../api/packages';
import { useAuth } from '../context/AuthContext';

export default function DashboardPage() {
  const [packages, setPackages] = useState([]);
  const [loading, setLoading] = useState(true);

  const [page, setPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [hasNext, setHasNext] = useState(false);
  const [hasPrev, setHasPrev] = useState(false);

  const navigate = useNavigate();

  const { user, logout } = useAuth();

  useEffect(() => {
    const fetchPackages = async () => {
      try {
        setLoading(true);

        const res = await listPackages(page);

        setPackages(res.data.results);
        setTotalCount(res.data.count);
        setHasNext(!!res.data.next);
        setHasPrev(!!res.data.previous);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchPackages();
  }, [page]);

  const getStatusColor = (status) => {
    switch (status) {
      case 'DRAFT':
        return '#f59e0b';

      case 'SENT':
        return '#2563eb';

      case 'COMPLETED':
        return '#16a34a';

      default:
        return '#6b7280';
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div>
          <h1 style={styles.title}>Dashboard</h1>

          <p style={styles.subtitle}>
            Welcome back, {user?.email}
          </p>
        </div>

        <div style={styles.headerActions}>
          <button
            onClick={() => navigate('/upload')}
            style={styles.newBtn}
          >
            + New Package
          </button>

          <button
            onClick={() => navigate('/webhooks')}
            style={styles.webhooksBtn}
          >
            🔔 Webhooks
          </button>

          <button
            onClick={logout}
            style={styles.logoutBtn}
          >
            Logout
          </button>
        </div>
      </div>

      {loading ? (
        <div style={styles.emptyState}>
          <p>Loading packages...</p>
        </div>
      ) : packages.length === 0 ? (
        <div style={styles.emptyState}>
          <h3>No packages yet</h3>

          <p>
            Create your first signing package to get started.
          </p>
        </div>
      ) : (
        <div style={styles.packageGrid}>
          {packages.map((pkg) => (
            <div
              key={pkg.id}
              style={styles.packageCard}
              onClick={() => navigate(`/packages/${pkg.id}`)}
            >
              <div style={styles.cardTop}>
                <h3 style={styles.packageTitle}>
                  {pkg.subject}
                </h3>

                <span
                  style={{
                    ...styles.statusBadge,
                    background: getStatusColor(pkg.status),
                  }}
                >
                  {pkg.status}
                </span>
              </div>

              <div style={styles.cardInfo}>
                <p>
                  <strong>Recipients:</strong>{' '}
                  {pkg.recipient_count}
                </p>

                <p>
                  <strong>Routing:</strong>{' '}
                  {pkg.routing_mode}
                </p>

                <p>
                  <strong>Created:</strong>{' '}
                  {new Date(pkg.created_at).toLocaleDateString()}
                </p>
              </div>
            </div>
          ))}
          {totalCount > 10 && (
            <div style={styles.pagination}>
              <span style={styles.pageInfo}>
                Showing page {page} · {totalCount} total packages
              </span>
              <div style={styles.pageControls}>
                <button
                  onClick={() => setPage(p => p - 1)}
                  disabled={!hasPrev}
                  style={styles.pageBtn}
                >
                  ← Previous
                </button>
                <button
                  onClick={() => setPage(p => p + 1)}
                  disabled={!hasNext}
                  style={styles.pageBtn}
                >
                  Next →
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

const styles = {
  container: {
    minHeight: '100vh',
    background: '#f5f5f5',
    padding: '2rem',
  },

  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '2rem',
  },

  title: {
    marginBottom: '0.3rem',
  },

  subtitle: {
    color: '#666',
  },

  headerActions: {
    display: 'flex',
    gap: '1rem',
  },

  newBtn: {
    padding: '0.75rem 1.2rem',
    background: '#2563eb',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    fontWeight: '500',
  },

  logoutBtn: {
    padding: '0.75rem 1.2rem',
    background: '#ef4444',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    fontWeight: '500',
  },

  webhooksBtn: {
    padding: '0.75rem 1.2rem',
    background: '#7c3aed',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    fontWeight: '500',
  },

  emptyState: {
    background: 'white',
    padding: '3rem',
    borderRadius: '8px',
    textAlign: 'center',
    boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
  },

  packageGrid: {
    display: 'grid',
    gap: '1rem',
  },

  packageCard: {
    background: 'white',
    borderRadius: '8px',
    padding: '1.5rem',
    cursor: 'pointer',
    transition: '0.2s',
    boxShadow: '0 2px 10px rgba(0,0,0,0.08)',
  },

  cardTop: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '1rem',
  },

  packageTitle: {
    margin: 0,
  },

  statusBadge: {
    color: 'white',
    padding: '0.35rem 0.8rem',
    borderRadius: '999px',
    fontSize: '0.8rem',
    fontWeight: '600',
  },

  cardInfo: {
    color: '#555',
    lineHeight: '1.8',
  },
  pagination: {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginTop: '1rem',
  padding: '0.75rem 0',
  },
  pageInfo: { color: '#666', fontSize: '0.85rem' },
  pageControls: { display: 'flex', gap: '0.5rem' },
  pageBtn: {
    padding: '0.4rem 0.8rem',
    background: 'white',
    border: '1px solid #ddd',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '0.85rem',
  },
};