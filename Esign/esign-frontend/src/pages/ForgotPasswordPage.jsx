// src/pages/ForgotPasswordPage.jsx

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'react-toastify';
import { forgotPassword } from '../api/auth';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      await forgotPassword(email);
      setSubmitted(true);
      toast.success('If that email is registered, a reset link has been sent.');
    } catch (err) {
      toast.error('Something went wrong. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h1 style={styles.title}>eSign</h1>
        <h2 style={styles.heading}>Forgot Password</h2>
        <p style={styles.subtitle}>
          Enter your email and we'll send you a password reset link.
        </p>

        {submitted ? (
          <div style={styles.successBox}>
            <p style={styles.successText}>
              ✓ Check your inbox — a reset link is on its way.
            </p>
            <p style={styles.successSub}>
              Didn't receive it? Check your spam folder.
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit}>
            <div style={styles.field}>
              <label>Email address</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                placeholder="you@example.com"
                style={styles.input}
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              style={styles.button}
            >
              {loading ? 'Sending...' : 'Send Reset Link'}
            </button>
          </form>
        )}

        <p style={styles.link}>
          <Link to="/login">← Back to Sign In</Link>
        </p>
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
  title: { textAlign: 'center', marginBottom: '0.25rem', fontSize: '1.5rem' },
  heading: { textAlign: 'center', marginBottom: '0.5rem', fontSize: '1.2rem' },
  subtitle: { textAlign: 'center', color: '#666', marginBottom: '1.5rem', fontSize: '0.9rem' },
  field: { marginBottom: '1.25rem' },
  input: {
    width: '100%',
    padding: '0.65rem',
    marginTop: '0.3rem',
    border: '1px solid #ddd',
    borderRadius: '4px',
    fontSize: '1rem',
    boxSizing: 'border-box',
  },
  button: {
    width: '100%',
    padding: '0.75rem',
    background: '#2563eb',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    fontSize: '1rem',
    cursor: 'pointer',
    marginTop: '0.25rem',
  },
  successBox: {
    background: '#dcfce7',
    border: '1px solid #86efac',
    borderRadius: '6px',
    padding: '1.25rem',
    marginBottom: '1rem',
    textAlign: 'center',
  },
  successText: { color: '#166534', fontWeight: '600', marginBottom: '0.5rem' },
  successSub: { color: '#166534', fontSize: '0.85rem' },
  link: { textAlign: 'center', marginTop: '1.25rem', fontSize: '0.9rem' },
};
