// src/pages/TemplatesPage.jsx

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { listTemplates, useTemplate } from '../api/documents';

export default function TemplatesPage() {
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetchTemplates();
  }, []);

  const fetchTemplates = async () => {
    try {
      const res = await listTemplates();
      setTemplates(res.data.results || res.data);
    } catch (err) {
      toast.error('Failed to load templates.');
    } finally {
      setLoading(false);
    }
  };

  const handleUseTemplate = async (templateId) => {
    try {
      const res = await useTemplate(templateId);
      toast.success(res.data.message);
      // Navigate to create package page with the new document ID
      navigate(`/packages/new?documentId=${res.data.document_id}&documentName=${encodeURIComponent(res.data.original_filename)}`);
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to use template.');
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h1 style={styles.title}>Document Templates</h1>
        <p style={styles.subtitle}>Reusable templates for standard forms and contracts.</p>
      </div>

      {loading ? (
        <p>Loading templates...</p>
      ) : templates.length === 0 ? (
        <div style={styles.emptyState}>
          <p>No templates found. Upload a document to create a template.</p>
        </div>
      ) : (
        <div style={styles.grid}>
          {templates.map(tpl => (
            <div key={tpl.id} style={styles.card}>
              <div style={styles.cardHeader}>
                <h3 style={styles.cardTitle}>{tpl.name}</h3>
                <span style={styles.versionBadge}>v{tpl.version}</span>
              </div>
              <p style={styles.cardDesc}>{tpl.description || 'No description provided.'}</p>
              
              <div style={styles.metaData}>
                <p><strong>Document:</strong> {tpl.document_name}</p>
                <p><strong>Times Used:</strong> {tpl.use_count}</p>
                {tpl.is_locked && <p style={styles.locked}>🔒 Locked</p>}
              </div>

              <div style={styles.actions}>
                <button 
                  onClick={() => handleUseTemplate(tpl.id)}
                  style={styles.primaryBtn}
                >
                  Use Template
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

const styles = {
  container: { padding: '2rem', maxWidth: '1200px', margin: '0 auto' },
  header: { marginBottom: '2rem' },
  title: { margin: '0 0 0.5rem 0', fontSize: '1.8rem', color: '#111827' },
  subtitle: { margin: 0, color: '#6b7280', fontSize: '1rem' },
  emptyState: { padding: '3rem', textAlign: 'center', background: '#f9fafb', borderRadius: '8px', border: '1px dashed #d1d5db', color: '#6b7280' },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '1.5rem' },
  card: { background: 'white', borderRadius: '8px', padding: '1.5rem', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', border: '1px solid #e5e7eb', display: 'flex', flexDirection: 'column' },
  cardHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' },
  cardTitle: { margin: 0, fontSize: '1.1rem', fontWeight: '600', color: '#1f2937' },
  versionBadge: { background: '#f3f4f6', color: '#4b5563', padding: '2px 6px', borderRadius: '4px', fontSize: '0.75rem', fontWeight: '600' },
  cardDesc: { margin: '0 0 1rem 0', color: '#4b5563', fontSize: '0.9rem', flex: 1 },
  metaData: { background: '#f9fafb', padding: '0.75rem', borderRadius: '6px', fontSize: '0.85rem', color: '#374151', marginBottom: '1.5rem' },
  locked: { color: '#dc2626', fontWeight: '600', marginTop: '0.25rem' },
  actions: { marginTop: 'auto', display: 'flex', gap: '0.5rem' },
  primaryBtn: { width: '100%', padding: '0.6rem', background: '#2563eb', color: 'white', border: 'none', borderRadius: '4px', fontWeight: '500', cursor: 'pointer' }
};
