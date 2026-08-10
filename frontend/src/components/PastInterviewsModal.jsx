import React, { useState, useEffect } from 'react';
import { Sparkles, Calendar, Clock, Award, CheckCircle, ChevronRight, X, BarChart2, BookOpen, AlertCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import styles from './PastInterviewsModal.module.css';

export default function PastInterviewsModal({ isOpen, onClose, onSelectReport }) {
  const { user, fetchUserInterviews } = useAuth();
  const [interviews, setInterviews] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (isOpen) {
      loadHistory();
    }
  }, [isOpen, user]);

  const loadHistory = async () => {
    setLoading(true);
    try {
      const data = await fetchUserInterviews();
      setInterviews(data);
    } catch (e) {
      console.error('Error loading history:', e);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  // Calculate summary metrics
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
    <div className={styles.modalOverlay} onClick={onClose}>
      <div className={styles.modalCard} onClick={(e) => e.stopPropagation()}>
        <div className={styles.modalHeader}>
          <div>
            <div className={styles.badge}>
              <BarChart2 size={14} /> Performance History
            </div>
            <h2>Past Interview Reports</h2>
            <p>Review your interview performance, questions solved, and AI evaluation feedback.</p>
          </div>
          <button className={styles.closeBtn} onClick={onClose} aria-label="Close">
            <X size={18} />
          </button>
        </div>

        {/* Top Summary Stats */}
        <div className={styles.statsGrid}>
          <div className={styles.statCard}>
            <div className={styles.statLabel}>Total Interviews</div>
            <div className={styles.statValue}>{totalCount}</div>
          </div>
          <div className={styles.statCard}>
            <div className={styles.statLabel}>Average Score</div>
            <div className={styles.statValue} style={{ color: avgScore !== 'N/A' && avgScore >= 7 ? '#10b981' : '#f59e0b' }}>
              {avgScore} {avgScore !== 'N/A' && <span className={styles.statMax}>/ 10</span>}
            </div>
          </div>
          <div className={styles.statCard}>
            <div className={styles.statLabel}>Hiring Recommendations</div>
            <div className={styles.statValue} style={{ color: '#60a5fa' }}>
              {strongHireCount} <span className={styles.statMax}>/ {totalCount}</span>
            </div>
          </div>
        </div>

        {/* Interview List */}
        <div className={styles.interviewListContainer}>
          {loading ? (
            <div className={styles.loadingState}>
              <div className={styles.spinner}></div>
              <p>Loading your interview history...</p>
            </div>
          ) : interviews.length === 0 ? (
            <div className={styles.emptyState}>
              <BookOpen size={36} className={styles.emptyIcon} />
              <h3>No Past Interviews Found</h3>
              <p>Complete a mock interview with Sanya / Shubh to see your detailed performance report and analytics here.</p>
            </div>
          ) : (
            <div className={styles.interviewList}>
              {interviews.map((item, idx) => {
                const score = item.overall_score || 0;
                const scoreColor = getScoreColor(score);
                const isHire = (item.recommendation || '').toLowerCase().includes('hire');

                return (
                  <div key={item.session_id || idx} className={styles.interviewCard}>
                    <div className={styles.cardHeader}>
                      <div className={styles.cardHeaderLeft}>
                        <span className={styles.trackBadge}>
                          {item.track_name || (item.track ? `${item.track.toUpperCase()} Tier` : 'Technical Track')}
                        </span>
                        <span className={styles.dateText}>
                          <Calendar size={13} /> {formatDate(item.created_at)}
                        </span>
                        <span className={styles.durationText}>
                          <Clock size={13} /> {item.total_time_minutes || '20 Mins'}
                        </span>
                      </div>
                      <div className={styles.cardScoreBadge} style={{ borderColor: scoreColor, color: scoreColor }}>
                        <strong>{score.toFixed(1)}</strong> / 10
                      </div>
                    </div>

                    <div className={styles.cardBody}>
                      <div className={styles.questionsList}>
                        <div className={styles.qItem}>
                          <span className={styles.qLabel}>Q1:</span>
                          <span className={styles.qTitle}>{item.q1_title || 'Question 1'}</span>
                        </div>
                        {item.q2_title && (
                          <div className={styles.qItem}>
                            <span className={styles.qLabel}>Q2:</span>
                            <span className={styles.qTitle}>{item.q2_title}</span>
                          </div>
                        )}
                      </div>

                      <div className={styles.recBadge} style={{ 
                        background: isHire ? 'rgba(16, 185, 129, 0.12)' : 'rgba(245, 158, 11, 0.12)',
                        color: isHire ? '#34d399' : '#fbbf24',
                        borderColor: isHire ? 'rgba(16, 185, 129, 0.3)' : 'rgba(245, 158, 11, 0.3)'
                      }}>
                        <Award size={14} /> {item.recommendation || 'Evaluated'}
                      </div>
                    </div>

                    <div className={styles.cardFooter}>
                      <div className={styles.attemptedText}>
                        Questions Attempted: <strong>{item.total_questions_attempted || '2 / 2'}</strong>
                      </div>
                      <button 
                        className={styles.viewReportBtn}
                        onClick={() => {
                          onSelectReport(item);
                          onClose();
                        }}
                      >
                        View Full Report <ChevronRight size={15} />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
