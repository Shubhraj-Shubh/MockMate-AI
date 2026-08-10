import React, { useState, useEffect } from 'react';
import {
  Sparkles, Play, BarChart2, Calendar, Clock, Award,
  ChevronRight, LogOut, User, BookOpen, CheckCircle, Code, ShieldCheck
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import styles from './HomeDashboard.module.css';

export default function HomeDashboard({ onStartInterview, onSelectReport }) {
  const { user, logout, fetchUserInterviews } = useAuth();
  const [interviews, setInterviews] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadHistory();
  }, [user]);

  const loadHistory = async () => {
    setLoading(true);
    try {
      const data = await fetchUserInterviews();
      setInterviews(data);
    } catch (e) {
      console.error('Failed to load interviews:', e);
    } finally {
      setLoading(false);
    }
  };

  const totalCount = interviews.length;
  const avgScore = totalCount > 0
    ? (interviews.reduce((acc, curr) => acc + (curr.overall_score || 0), 0) / totalCount).toFixed(1)
    : 'N/A';

  const strongHireCount = interviews.filter(i => (i.recommendation || '').toLowerCase().includes('hire')).length;

  const formatDate = (timestamp) => {
    if (!timestamp) return 'Recent';
    const d = new Date(typeof timestamp === 'number' && timestamp < 1e12 ? timestamp * 1000 : timestamp);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  const getScoreColor = (score) => {
    if (score >= 8.0) return '#10B981';
    if (score >= 6.0) return '#3B82F6';
    if (score >= 4.0) return '#F59E0B';
    return '#EF4444';
  };

  return (
    <div className={styles.dashboardContainer}>
      {/* Top Navigation */}
      <header className={styles.navbar}>
        <div className={styles.logo}>
          <div className={styles.logoIcon}>
            <Sparkles size={18} className={styles.logoSparkle} />
          </div>
          <div className={styles.brandTitle}>
            MockMate<span className={styles.logoAccent}>.ai</span>
          </div>
          <span className={styles.badge}>Candidate Hub</span>
        </div>

        <div className={styles.navRight}>
          <div className={styles.userBadge}>
            <div className={styles.userAvatar}>
              <User size={15} />
            </div>
            <div className={styles.userInfo}>
              <span className={styles.userName}>{user?.name || 'Candidate'}</span>
              <span className={styles.userUsername}>{user?.username}</span>
            </div>
          </div>

          <button className={styles.logoutBtn} onClick={logout} title="Sign Out">
            <LogOut size={16} />
            <span>Sign Out</span>
          </button>
        </div>
      </header>

      {/* Main Hub Body */}
      <main className={styles.mainContent}>
        {/* Welcome Hero Banner */}
        <section className={styles.heroBanner}>
          <div className={styles.heroLeft}>
            <div className={styles.welcomeTag}>
              <Sparkles size={15} /> Ready for your next challenge
            </div>
            <h1 className={styles.welcomeTitle}>
              Welcome back, <span className={styles.nameHighlight}>{user?.name || 'Candidate'}</span>!
            </h1>
            <p className={styles.welcomeSubtitle}>
              Practice voice-driven coding interviews with Senior Interviewer Sanya / Shubh. Choose your difficulty tier and get real-time Socratic feedback.
            </p>

            <button className={styles.primaryCtaBtn} onClick={onStartInterview}>
              <Play size={18} fill="currentColor" /> Take Mock Interview
            </button>
          </div>

          <div className={styles.tierCardsContainer}>
            <div className={styles.tierCard}>
              <div className={styles.tierHeader}>
                <span className={styles.tierDot} style={{ background: '#10B981' }}></span>
                <h4>Easy Tier</h4>
              </div>
              <p>60 min • 2 Mediums</p>
              <span className={styles.tierTag}>Core DSA & Patterns</span>
            </div>

            <div className={`${styles.tierCard} ${styles.tierCardFeatured}`}>
              <div className={styles.featuredBadge}>Popular</div>
              <div className={styles.tierHeader}>
                <span className={styles.tierDot} style={{ background: '#F59E0B' }}></span>
                <h4>Medium Tier</h4>
              </div>
              <p>60 min • 1 Med + 1 Hard</p>
              <span className={styles.tierTag}>Adaptive Difficulty</span>
            </div>

            <div className={styles.tierCard}>
              <div className={styles.tierHeader}>
                <span className={styles.tierDot} style={{ background: '#EF4444' }}></span>
                <h4>Hard Tier</h4>
              </div>
              <p>60 min • 2 Hards</p>
              <span className={styles.tierTag}>Advanced & Scale</span>
            </div>

            <div className={`${styles.tierCard} ${styles.tierCardFeatured}`} style={{ borderColor: 'rgba(168, 85, 247, 0.4)' }}>
              <div className={styles.featuredBadge} style={{ background: '#a855f7' }}>New Mode</div>
              <div className={styles.tierHeader}>
                <span className={styles.tierDot} style={{ background: '#A855F7' }}></span>
                <h4>CV Grilling</h4>
              </div>
              <p>25-30 min Deep-Dive</p>
              <span className={styles.tierTag} style={{ background: 'rgba(168, 85, 247, 0.15)', color: '#d8b4fe' }}>Projects & Trade-offs</span>
            </div>
          </div>
        </section>

        {/* Analytics Summary */}
        <section className={styles.statsSection}>
          <div className={styles.statCard}>
            <div className={styles.statLabel}>Total Interviews Taken</div>
            <div className={styles.statNumber}>{totalCount}</div>
          </div>

          <div className={styles.statCard}>
            <div className={styles.statLabel}>Average Performance Score</div>
            <div className={styles.statNumber} style={{ color: avgScore !== 'N/A' && avgScore >= 7 ? '#10b981' : '#f59e0b' }}>
              {avgScore} {avgScore !== 'N/A' && <span className={styles.statMax}>/ 10</span>}
            </div>
          </div>

          <div className={styles.statCard}>
            <div className={styles.statLabel}>Hiring Recommendations</div>
            <div className={styles.statNumber} style={{ color: '#60a5fa' }}>
              {strongHireCount} <span className={styles.statMax}>/ {totalCount}</span>
            </div>
          </div>
        </section>

        {/* Recent Interviews History Section */}
        <section className={styles.historySection}>
          <div className={styles.sectionHeader}>
            <div className={styles.sectionTitleGroup}>
              <BarChart2 size={20} className={styles.sectionIcon} />
              <h2>Your Past Interview Reports</h2>
            </div>
            <span className={styles.historyCount}>{totalCount} Completed</span>
          </div>

          {loading ? (
            <div className={styles.loadingContainer}>
              <div className={styles.spinner}></div>
              <p>Loading your past interview reports...</p>
            </div>
          ) : interviews.length === 0 ? (
            <div className={styles.emptyContainer}>
              <BookOpen size={40} className={styles.emptyIcon} />
              <h3>No Mock Interviews Taken Yet</h3>
              <p>Click "Take Mock Interview" above to start your first session with Sanya / Shubh and receive a full evaluation report.</p>
            </div>
          ) : (
            <div className={styles.reportsGrid}>
              {interviews.map((item, idx) => {
                const score = item.overall_score || 0;
                const scoreColor = getScoreColor(score);
                const isHire = (item.recommendation || '').toLowerCase().includes('hire');

                return (
                  <div key={item.session_id || idx} className={styles.reportCard}>
                    <div className={styles.cardTop}>
                      <div className={styles.cardTrackGroup}>
                        <span className={styles.trackBadge}>
                          {item.track_name || (item.track ? `${item.track.toUpperCase()} Tier` : 'Technical Track')}
                        </span>
                        <span className={styles.dateBadge}>
                          <Calendar size={12} /> {formatDate(item.created_at)}
                        </span>
                        <span className={styles.durationBadge}>
                          <Clock size={12} /> {item.total_time_minutes || '20 Mins'}
                        </span>
                      </div>

                      <div className={styles.scorePill} style={{ borderColor: scoreColor, color: scoreColor }}>
                        <strong>{score.toFixed(1)}</strong> / 10
                      </div>
                    </div>

                    <div className={styles.cardQuestions}>
                      <div className={styles.qRow}>
                        <span className={styles.qPrefix}>Q1:</span>
                        <span className={styles.qName}>{item.q1_title || 'Question 1'}</span>
                      </div>
                      {item.q2_title && (
                        <div className={styles.qRow}>
                          <span className={styles.qPrefix}>Q2:</span>
                          <span className={styles.qName}>{item.q2_title}</span>
                        </div>
                      )}
                    </div>

                    <div className={styles.cardBottom}>
                      <div className={styles.recTag} style={{
                        background: isHire ? 'rgba(16, 185, 129, 0.12)' : 'rgba(245, 158, 11, 0.12)',
                        color: isHire ? '#34d399' : '#fbbf24',
                        borderColor: isHire ? 'rgba(16, 185, 129, 0.3)' : 'rgba(245, 158, 11, 0.3)'
                      }}>
                        <Award size={13} /> {item.recommendation || 'Evaluated'}
                      </div>

                      <button
                        className={styles.viewReportBtn}
                        onClick={() => onSelectReport(item)}
                      >
                        View Full Report <ChevronRight size={15} />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
