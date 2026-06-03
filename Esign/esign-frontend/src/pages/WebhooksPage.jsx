// src/pages/WebhooksPage.jsx

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { listWebhooks, createWebhook, updateWebhook, deleteWebhook } from '../api/packages';

const ALL_EVENTS = [
  'package.created',
  'package.sent',
  'package.completed',
  'package.expired',
  'package.declined',
  'package.cancelled',
  'signing.viewed',
  'signing.signed',
  'reminder.sent',
];

function WebhookForm({ initial, onSave, onCancel }) {
  const [url, setUrl]       = useState(initial?.url || '');
  const [secret, setSecret] = useState(initial?.secret || '');
  const [events, setEvents] = useState(initial?.events || []);
  const [saving, setSaving] = useState(false);

  const toggle = (evt) =>
    setEvents((prev) =>
      prev.includes(evt) ? prev.filter((e) => e !== evt) : [...prev, evt]
    );

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!url) { toast.error('URL is required.'); return; }
    if (events.length === 0) { toast.error('Select at least one event.'); return; }

    setSaving(true);
    try {
      await onSave({ url, secret, events });
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} style={styles.form}>
      <div style={styles.field}>
        <label style={styles.label}>Endpoint URL *</label>
        <input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          required
          placeholder="https://yourserver.com/webhook"
          style={styles.input}
        />
      </div>
      <div style={styles.field}>
        <label style={styles.label}>Secret (optional)</label>
        <input
          value={secret}
          onChange={(e) => setSecret(e.target.value)}
          placeholder="Used to verify HMAC signature"
          style={styles.input}
        />
      </div>
      <div style={styles.field}>
        <label style={styles.label}>Events *</label>
        <div style={styles.eventsGrid}>
          {ALL_EVENTS.map((evt) => (
            <label key={evt} style={styles.evtLabel}>
              <input
                type="checkbox"
                checked={events.includes(evt)}
                onChange={() => toggle(evt)}
                style={{ marginRight: '0.4rem' }}
              />
              {evt}
            </label>
          ))}
        </div>
      </div>
      <div style={styles.formActions}>
        <button type="button" onClick={onCancel} style={styles.cancelBtn}>
          Cancel
        </button>
        <button type="submit" disabled={saving} style={styles.saveBtn}>
          {saving ? 'Saving…' : initial ? 'Update Webhook' : 'Create Webhook'}
        </button>
      </div>
    </form>
  );
}

export default function WebhooksPage() {
  const navigate = useNavigate();
  const [webhooks, setWebhooks]   = useState([]);
  const [loading, setLoading]     = useState(true);
  const [creating, setCreating]   = useState(false);
  const [editingId, setEditingId] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const res = await listWebhooks();
      setWebhooks(res.data);
    } catch {
      toast.error('Failed to load webhooks.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async (data) => {
    try {
      await createWebhook(data);
      toast.success('Webhook created!');
      setCreating(false);
      load();
    } catch {
      toast.error('Failed to create webhook.');
    }
  };

  const handleUpdate = async (id, data) => {
    try {
      await updateWebhook(id, data);
      toast.success('Webhook updated!');
      setEditingId(null);
      load();
    } catch {
      toast.error('Failed to update webhook.');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this webhook?')) return;
    try {
      await deleteWebhook(id);
      toast.success('Webhook deleted.');
      load();
    } catch {
      toast.error('Failed to delete webhook.');
    }
  };

  const handleToggle = async (wh) => {
    try {
      await updateWebhook(wh.id, { is_active: !wh.is_active });
      toast.success(wh.is_active ? 'Webhook disabled.' : 'Webhook enabled.');
      load();
    } catch {
      toast.error('Failed to toggle webhook.');
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <button onClick={() => navigate('/')} style={styles.backBtn}>
          ← Dashboard
        </button>
        <div>
          <h2 style={styles.title}>Webhooks</h2>
          <p style={styles.subtitle}>
            Get notified at your own URL when package events happen.
          </p>
        </div>
        {!creating && (
          <button onClick={() => setCreating(true)} style={styles.newBtn}>
            + New Webhook
          </button>
        )}
      </div>

      <div style={styles.body}>
        {creating && (
          <div style={styles.card}>
            <h3 style={styles.cardTitle}>New Webhook</h3>
            <WebhookForm
              onSave={handleCreate}
              onCancel={() => setCreating(false)}
            />
          </div>
        )}

        {loading ? (
          <p style={styles.empty}>Loading…</p>
        ) : webhooks.length === 0 && !creating ? (
          <div style={styles.emptyCard}>
            <p style={styles.emptyTitle}>No webhooks yet</p>
            <p style={styles.emptySub}>
              Create one to start receiving real-time event notifications.
            </p>
            <button onClick={() => setCreating(true)} style={styles.newBtn}>
              + New Webhook
            </button>
          </div>
        ) : (
          webhooks.map((wh) => (
            <div key={wh.id} style={styles.card}>
              {editingId === wh.id ? (
                <>
                  <h3 style={styles.cardTitle}>Edit Webhook</h3>
                  <WebhookForm
                    initial={wh}
                    onSave={(data) => handleUpdate(wh.id, data)}
                    onCancel={() => setEditingId(null)}
                  />
                </>
              ) : (
                <>
                  <div style={styles.whHeader}>
                    <div>
                      <p style={styles.whUrl}>{wh.url}</p>
                      <div style={styles.evtTags}>
                        {wh.events.map((e) => (
                          <span key={e} style={styles.evtTag}>{e}</span>
                        ))}
                      </div>
                    </div>
                    <div style={styles.whActions}>
                      <span style={{
                        ...styles.statusBadge,
                        background: wh.is_active ? '#dcfce7' : '#fee2e2',
                        color: wh.is_active ? '#166534' : '#991b1b',
                      }}>
                        {wh.is_active ? 'Active' : 'Disabled'}
                      </span>
                      <button onClick={() => handleToggle(wh)} style={styles.iconBtn} title="Toggle">
                        {wh.is_active ? '⏸' : '▶'}
                      </button>
                      <button onClick={() => setEditingId(wh.id)} style={styles.iconBtn} title="Edit">
                        ✏️
                      </button>
                      <button
                        onClick={() => handleDelete(wh.id)}
                        style={{ ...styles.iconBtn, color: '#dc2626' }}
                        title="Delete"
                      >
                        🗑
                      </button>
                    </div>
                  </div>
                  <p style={styles.whMeta}>
                    Created {new Date(wh.created_at).toLocaleDateString()}
                    {wh.secret && ' · Secret configured ✓'}
                  </p>
                </>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

const styles = {
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
    padding: '0.4rem 0.8rem', background: 'transparent',
    border: '1px solid #ddd', borderRadius: '4px', cursor: 'pointer',
    fontSize: '0.9rem', whiteSpace: 'nowrap',
  },
  title: { margin: 0, marginBottom: '0.15rem' },
  subtitle: { margin: 0, color: '#666', fontSize: '0.85rem' },
  newBtn: {
    marginLeft: 'auto', padding: '0.6rem 1.1rem',
    background: '#2563eb', color: 'white', border: 'none',
    borderRadius: '6px', cursor: 'pointer', fontWeight: '500',
    whiteSpace: 'nowrap',
  },
  body: { maxWidth: '760px', margin: '2rem auto', padding: '0 1rem' },
  card: {
    background: 'white', borderRadius: '8px', padding: '1.5rem',
    marginBottom: '1rem', boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
  },
  cardTitle: { margin: '0 0 1.25rem', fontSize: '1rem' },
  empty:   { textAlign: 'center', color: '#999', padding: '2rem 0' },
  emptyCard: {
    background: 'white', borderRadius: '8px', padding: '3rem 2rem',
    textAlign: 'center', boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
  },
  emptyTitle: { fontWeight: '600', fontSize: '1.1rem', marginBottom: '0.5rem' },
  emptySub:   { color: '#666', fontSize: '0.9rem', marginBottom: '1.5rem' },
  whHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem' },
  whUrl:    { fontWeight: '600', fontSize: '0.95rem', marginBottom: '0.5rem', wordBreak: 'break-all' },
  evtTags:  { display: 'flex', flexWrap: 'wrap', gap: '0.35rem' },
  evtTag: {
    background: '#eff6ff', color: '#1d4ed8', padding: '0.15rem 0.5rem',
    borderRadius: '999px', fontSize: '0.75rem',
  },
  whActions: { display: 'flex', alignItems: 'center', gap: '0.5rem', flexShrink: 0 },
  whMeta:   { color: '#9ca3af', fontSize: '0.8rem', marginTop: '0.75rem' },
  statusBadge: {
    padding: '0.2rem 0.6rem', borderRadius: '999px',
    fontSize: '0.78rem', fontWeight: '600',
  },
  iconBtn: {
    padding: '0.3rem 0.5rem', background: 'transparent',
    border: '1px solid #e5e7eb', borderRadius: '4px', cursor: 'pointer',
    fontSize: '0.9rem',
  },
  form: {},
  field: { marginBottom: '1.1rem' },
  label: { display: 'block', marginBottom: '0.4rem', fontSize: '0.9rem', fontWeight: '500' },
  input: {
    width: '100%', padding: '0.6rem', border: '1px solid #ddd',
    borderRadius: '4px', fontSize: '0.95rem', boxSizing: 'border-box',
  },
  eventsGrid: { display: 'flex', flexWrap: 'wrap', gap: '0.5rem 1.5rem' },
  evtLabel:   { display: 'flex', alignItems: 'center', fontSize: '0.875rem', cursor: 'pointer' },
  formActions: { display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1.25rem' },
  cancelBtn: {
    padding: '0.55rem 1.1rem', background: 'transparent',
    border: '1px solid #ddd', borderRadius: '4px', cursor: 'pointer',
  },
  saveBtn: {
    padding: '0.55rem 1.4rem', background: '#2563eb', color: 'white',
    border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: '500',
  },
};
