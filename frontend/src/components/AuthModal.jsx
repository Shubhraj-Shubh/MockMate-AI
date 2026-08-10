import React, { useState } from 'react';
import { Sparkles, User, Mail, Lock, X, ArrowRight, Check } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import styles from './AuthModal.module.css';

export default function AuthModal({ isOpen, onClose }) {
  const { login, register } = useAuth();
  const [isLoginTab, setIsLoginTab] = useState(true);
  const [username, setUsername] = useState('');
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (isLoginTab) {
        await login(username, password);
      } else {
        await register(username, name, password);
      }
      onClose();
    } catch (err) {
      setError(err.message || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.modalOverlay} onClick={onClose}>
      <div className={styles.modalCard} onClick={(e) => e.stopPropagation()}>
        <button className={styles.closeBtn} onClick={onClose} aria-label="Close">
          <X size={18} />
        </button>

        <div className={styles.header}>
          <div className={styles.badge}>
            <Sparkles size={14} /> AI Interview Platform
          </div>
          <h2>{isLoginTab ? 'Welcome Back' : 'Create Account'}</h2>
          <p>{isLoginTab ? 'Sign in to access your interview history & analytics' : 'Sign up to track your performance and reports across interviews'}</p>
        </div>

        <div className={styles.tabContainer}>
          <button
            type="button"
            className={`${styles.tabBtn} ${isLoginTab ? styles.tabActive : ''}`}
            onClick={() => { setIsLoginTab(true); setError(''); }}
          >
            Sign In
          </button>
          <button
            type="button"
            className={`${styles.tabBtn} ${!isLoginTab ? styles.tabActive : ''}`}
            onClick={() => { setIsLoginTab(false); setError(''); }}
          >
            Register
          </button>
        </div>

        {error && (
          <div className={styles.errorBanner}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className={styles.form}>
          {!isLoginTab && (
            <div className={styles.inputGroup}>
              <label>Full Name</label>
              <div className={styles.inputWrapper}>
                <User size={16} className={styles.inputIcon} />
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Alex Chen"
                  required
                />
              </div>
            </div>
          )}

          <div className={styles.inputGroup}>
            <label>Username</label>
            <div className={styles.inputWrapper}>
              <User size={16} className={styles.inputIcon} />
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="you@example.com"
                required
              />
            </div>
          </div>

          <div className={styles.inputGroup}>
            <label>Password</label>
            <div className={styles.inputWrapper}>
              <Lock size={16} className={styles.inputIcon} />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={isLoginTab ? 'Enter your password' : 'At least 6 characters'}
                required
                minLength={6}
              />
            </div>
          </div>

          <button type="submit" className={styles.submitBtn} disabled={loading}>
            {loading ? 'Processing...' : (
              <>
                {isLoginTab ? 'Sign In' : 'Create Account'} <ArrowRight size={16} />
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
