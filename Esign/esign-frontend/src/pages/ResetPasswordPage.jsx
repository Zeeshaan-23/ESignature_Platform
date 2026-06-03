// src/pages/ResetPasswordPage.jsx

import { useState } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { toast } from 'react-toastify';
import { resetPassword } from '../api/auth';

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const uid   = searchParams.get('uid');
  const token = searchParams.get('token');

  const [newPassword, setNewPassword]       = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading]               = useState(false);
  const [done, setDone]                     = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (newPassword !== confirmPassword) {
      toast.error('Passwords do not match.');
      return;
    }
    if (newPassword.length < 8) {
      toast.error('Password must be at least 8 characters.');
      return;
    }

    setLoading(true);
    try {
      await resetPassword(uid, token, newPassword);
      setDone(true);
      toast.success('Password reset successfully!');
      setTimeout(() => navigate('/login'), 2500);
    } catch (err) {
      const msg = err.response?.data?.error || 'Invalid or expired reset link.';
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  if (!uid || !token) {
    return (
      <div style={styles.container}>
        <div style={styles.card}>
          <p style={{ color: 'red', textAlign: 'center' }}>
            Invalid reset link. Please request a new one.
          </p>
          <p style={styles.link}><Link to="/forgot-password">← Request new link</Link></p>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h1 style={styles.title}>eSign</h1>
        <h2 style={styles.heading}>Reset Password</h2>
        <p style={styles.subtitle}>Enter your new password below.</p>

        {done ? (
          <div style={styles.successBox}>
            <p style={styles.successText}>✓ Password reset successfully.</p>
            <p style={styles.successSub}>Redirecting to sign-in page…</p>
          </div>
        ) : (
          <form onSubmit={handleSubmit}>
            <div style={styles.field}>
              <label>New Password</label>
              <input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                minLength={8}
                style={styles.input}
              />
            </div>
            <div style={styles.field}>
              <label>Confirm Password</label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                style={styles.input}
              />
            </div>
            <button type="submit" disabled={loading} style={styles.button}>
              {loading ? 'Resetting…' : 'Reset Password'}
            </button>
          </form>
        )}

        <p style={styles.link}><Link to="/login">← Back to Sign In</Link></p>
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
    padding: '2.5rem',
    borderRadius: '8px',
    boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
    width: '100%',
    maxWidth: '420px',
  },
  title:    { textAlign: 'center', marginBottom: '0.25rem', fontSize: '1.5rem' },
  heading:  { textAlign: 'center', marginBottom: '0.5rem', fontSize: '1.2rem' },
  subtitle: { textAlign: 'center', color: '#666', marginBottom: '1.5rem', fontSize: '0.9rem' },
  field: { marginBottom: '1.25rem' },
  input: {
    width: '100%', padding: '0.65rem', marginTop: '0.3rem',
    border: '1px solid #ddd', borderRadius: '4px', fontSize: '1rem',
    boxSizing: 'border-box',
  },
  button: {
    width: '100%', padding: '0.75rem', background: '#2563eb',
    color: 'white', border: 'none', borderRadius: '4px',
    fontSize: '1rem', cursor: 'pointer', marginTop: '0.25rem',
  },
  successBox: {
    background: '#dcfce7', border: '1px solid #86efac',
    borderRadius: '6px', padding: '1.25rem',
    marginBottom: '1rem', textAlign: 'center',
  },
  successText: { color: '#166534', fontWeight: '600', marginBottom: '0.5rem' },
  successSub:  { color: '#166534', fontSize: '0.85rem' },
  link: { textAlign: 'center', marginTop: '1.25rem', fontSize: '0.9rem' },
};
