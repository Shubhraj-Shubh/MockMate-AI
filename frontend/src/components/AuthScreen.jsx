import React, { useState } from 'react';
import { Sparkles, User, Mail, Lock, ArrowRight, CheckCircle2, Terminal, Mic, ShieldCheck, Zap } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import styles from './AuthScreen.module.css';

export default function AuthScreen() {
  const { login, register } = useAuth();
  const [isLoginTab, setIsLoginTab] = useState(true);
  const [username, setUsername] = useState('');
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

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
    } catch (err) {
      setError(err.message || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.glowBg}></div>

      <div className={styles.contentGrid}>
        {/* Left Column: Hero & Features */}
        <div className={styles.heroSection}>
          <div className={styles.brandBadge}>
            <Sparkles size={16} /> Powered by Gemini & LangGraph
          </div>
          
          <h1 className={styles.heroTitle}>
            Master Your Technical DSA Interviews with <span className={styles.gradientText}>AI Interviewer Sanya / Shubh</span>
          </h1>

          <p className={styles.heroSubtitle}>
            Practice live voice-driven coding interviews with adaptive LeetCode questions, real-time code execution, Socratic guidance, and comprehensive hiring evaluations.
          </p>

          <div className={styles.featureList}>
            <div className={styles.featureItem}>
              <div className={styles.featureIcon} style={{ background: 'rgba(59, 130, 246, 0.15)', color: '#60a5fa' }}>
                <Mic size={18} />
              </div>
              <div>
                <h4>Real-Time Voice AI Interviewer</h4>
                <p>Natural conversation, project discussions, and live Socratic hints as you code.</p>
              </div>
            </div>

            <div className={styles.featureItem}>
              <div className={styles.featureIcon} style={{ background: 'rgba(16, 185, 129, 0.15)', color: '#34d399' }}>
                <Terminal size={18} />
              </div>
              <div>
                <h4>Automated LeetCode Integration</h4>
                <p>Dynamic question ingestion across Easy, Medium, and Hard difficulty tiers.</p>
              </div>
            </div>

            <div className={styles.featureItem}>
              <div className={styles.featureIcon} style={{ background: 'rgba(245, 158, 11, 0.15)', color: '#fbbf24' }}>
                <Zap size={18} />
              </div>
              <div>
                <h4>Dynamic Difficulty Adaptation</h4>
                <p>Questions adjust in real-time based on your problem-solving speed and accuracy.</p>
              </div>
            </div>

            <div className={styles.featureItem}>
              <div className={styles.featureIcon} style={{ background: 'rgba(168, 85, 247, 0.15)', color: '#c084fc' }}>
                <ShieldCheck size={18} />
              </div>
              <div>
                <h4>Evidence-Based Performance Reports</h4>
                <p>Section ratings on Problem Solving, Coding Skills, Communication, and Debugging.</p>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Authentication Card */}
        <div className={styles.authCardWrapper}>
          <div className={styles.authCard}>
            <div className={styles.cardHeader}>
              <h2>{isLoginTab ? 'Sign In to Your Account' : 'Create Free Account'}</h2>
              <p>{isLoginTab ? 'Access your dashboard, interview history, and performance reports' : 'Join now to start taking AI-powered mock technical interviews'}</p>
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
                    placeholder="Enter your username"
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
                {loading ? 'Authenticating...' : (
                  <>
                    {isLoginTab ? 'Sign In & Open Dashboard' : 'Create Account & Start'} <ArrowRight size={16} />
                  </>
                )}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
