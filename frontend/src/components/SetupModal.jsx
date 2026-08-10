import { useState, useEffect, useRef } from 'react';
import { Briefcase, Building, Code, Sparkles, Check, FileText, X, Upload, RefreshCw, Layers, CheckCircle2, AlertCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { API_BASE_URL } from '../config';
import styles from './SetupModal.module.css';

const TRACKS = [
  {
    id: 'easy',
    name: 'Easy Tier',
    description: '1-hour DSA interview with 2 Medium-level questions focusing on core data structures and standard algorithms.',
    tag: '60 min • 2x Medium',
    color: '#10B981'
  },
  {
    id: 'medium',
    name: 'Medium Tier',
    description: '1-hour DSA interview with 1 Medium + 1 Hard question (dynamically adapts to Medium if needed).',
    tag: '60 min • Medium + Hard',
    color: '#F59E0B'
  },
  {
    id: 'hard',
    name: 'Hard Tier',
    description: '1-hour DSA interview with 2 Hard-level questions testing advanced algorithmic design, multi-pass patterns, and scale.',
    tag: '60 min • 2x Hard',
    color: '#EF4444'
  },
  {
    id: 'cv_grill',
    name: 'CV / Resume Grilling',
    description: '25-30 min deep-dive into your projects, architectural trade-offs, tech stack decisions, and scaling limits.',
    tag: '25-30 min Deep-Dive',
    color: '#A855F7'
  }
];

export default function SetupModal({ onStart, isOpen, onClose }) {
  const { user, token } = useAuth();
  const [candidateName, setCandidateName] = useState('Candidate');
  const [selectedTrack, setSelectedTrack] = useState('medium');
  const [resumeBio, setResumeBio] = useState('Software Engineering candidate with experience in Python, algorithms, and backend systems.');
  const [preferredLang, setPreferredLang] = useState('python');

  // CV State
  const [userCv, setUserCv] = useState(null);
  const [isReplacingCv, setIsReplacingCv] = useState(false);
  const [uploadingCv, setUploadingCv] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    if (user?.name) {
      setCandidateName(user.name);
    }
    if (user?.email && isOpen) {
      fetchUserCv();
    }
  }, [user, isOpen]);

  const fetchUserCv = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/user/cv?email=${encodeURIComponent(user?.email || '')}`, {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {}
      });
      if (res.ok) {
        const data = await res.json();
        if (data.has_cv) {
          setUserCv(data);
          if (data.preview_text) {
            setResumeBio(data.preview_text);
          }
        }
      }
    } catch (e) {
      console.warn('Could not fetch user CV:', e);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadingCv(true);
    setUploadError(null);

    const formData = new FormData();
    formData.append('file', file);
    if (user?.email) {
      formData.append('email', user.email);
    }

    try {
      const res = await fetch(`${API_BASE_URL}/api/user/cv/upload`, {
        method: 'POST',
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
        body: formData
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to upload CV');
      }

      const data = await res.json();
      setUserCv(data);
      setIsReplacingCv(false);
      if (data.preview_text) {
        setResumeBio(data.preview_text);
      }
    } catch (err) {
      console.error('CV Upload Error:', err);
      setUploadError(err.message || 'Error processing CV file');
    } finally {
      setUploadingCv(false);
    }
  };

  if (!isOpen) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (selectedTrack === 'cv_grill' && !userCv?.has_cv && !resumeBio.trim()) {
      alert('Please upload your CV or provide a resume summary for the CV Grilling session.');
      return;
    }

    onStart({
      candidateName: candidateName.trim() || 'Candidate',
      track: selectedTrack,
      resumeBio: userCv?.preview_text || resumeBio.trim(),
      language: preferredLang,
      userEmail: user?.email || '',
      cvData: userCv
    });
  };

  const formatDate = (timestamp) => {
    if (!timestamp) return 'Recently';
    const d = new Date(typeof timestamp === 'number' && timestamp < 1e12 ? timestamp * 1000 : timestamp);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  return (
    <div className={styles.modalOverlay} onClick={onClose}>
      <div className={styles.modalCard} onClick={(e) => e.stopPropagation()}>
        {onClose && (
          <button className={styles.closeBtn} onClick={onClose} aria-label="Close">
            <X size={18} />
          </button>
        )}
        <div className={styles.header}>
          <div className={styles.badge}>
            <Sparkles size={16} /> AI Mock Interview Setup
          </div>
          <h2>Configure Your Interview Session</h2>
          <p>Choose your target track or select <strong>CV Grilling</strong> to be interrogated on your actual projects.</p>
        </div>

        <form onSubmit={handleSubmit} className={styles.form}>
          <div className={styles.inputGroup}>
            <label>Candidate Name</label>
            <input
              type="text"
              value={candidateName}
              onChange={(e) => setCandidateName(e.target.value)}
              placeholder="e.g. Alex Chen"
              required
            />
          </div>

          <div className={styles.inputGroup}>
            <label>Select Interview Mode</label>
            <div className={styles.trackGrid}>
              {TRACKS.map((t) => {
                const isSelected = selectedTrack === t.id;
                return (
                  <div
                    key={t.id}
                    className={`${styles.trackCard} ${isSelected ? styles.trackSelected : ''}`}
                    onClick={() => setSelectedTrack(t.id)}
                  >
                    <div className={styles.trackHeader}>
                      <span className={styles.trackTag} style={{ borderColor: t.color, color: t.color }}>
                        {t.tag}
                      </span>
                      {isSelected && <Check size={18} className={styles.checkIcon} />}
                    </div>
                    <h4>{t.name}</h4>
                    <p>{t.description}</p>
                  </div>
                );
              })}
            </div>
          </div>

          {/* CV Upload / Management Section */}
          <div className={styles.inputGroup}>
            <label>
              <FileText size={15} style={{ display: 'inline', verticalAlign: 'middle', marginRight: '4px' }} />
              Candidate CV / Resume {selectedTrack === 'cv_grill' && <span style={{ color: '#a855f7' }}>(Required for CV Grilling)</span>}
            </label>

            {userCv?.has_cv && !isReplacingCv ? (
              <div className={styles.cvCard}>
                <div className={styles.cvHeader}>
                  <div className={styles.cvInfo}>
                    <div className={styles.cvIconBox}>
                      <FileText size={20} />
                    </div>
                    <div className={styles.cvDetails}>
                      <h4>{userCv.filename || 'Candidate_Resume.pdf'}</h4>
                      <div className={styles.cvMeta}>
                        <span>Uploaded: {formatDate(userCv.uploaded_at)}</span>
                        {userCv.parsed_data?.projects?.length > 0 && (
                          <span>&bull; {userCv.parsed_data.projects.length} Projects Identified</span>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className={styles.cvActions}>
                    <span className={styles.cvBadge}>
                      <CheckCircle2 size={12} style={{ display: 'inline', verticalAlign: 'middle', marginRight: '3px' }} />
                      CV Ready
                    </span>
                    <button
                      type="button"
                      className={styles.cvActionBtn}
                      onClick={() => setIsReplacingCv(true)}
                    >
                      <RefreshCw size={12} /> Replace CV
                    </button>
                  </div>
                </div>

                {userCv.parsed_data?.projects?.length > 0 && (
                  <div className={styles.cvProjectsPills}>
                    {userCv.parsed_data.projects.map((p, idx) => (
                      <span key={idx} className={styles.cvProjectPill}>
                        {p.name}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div>
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileUpload}
                  accept=".pdf,.docx,.txt,.md"
                  style={{ display: 'none' }}
                />
                <div
                  className={styles.cvDropzone}
                  onClick={() => fileInputRef.current?.click()}
                >
                  <Upload size={24} color="#a855f7" />
                  <div className={styles.dropzoneTitle}>
                    {uploadingCv ? 'Extracting & Parsing CV with AI...' : 'Click to Upload CV / Resume'}
                  </div>
                  <div className={styles.dropzoneSub}>
                    Supports PDF, DOCX, TXT. Julie will extract your projects, tech stack, and key claims.
                  </div>
                  {isReplacingCv && (
                    <button
                      type="button"
                      className={styles.cvActionBtn}
                      onClick={(e) => { e.stopPropagation(); setIsReplacingCv(false); }}
                      style={{ marginTop: '0.25rem' }}
                    >
                      Cancel / Keep Existing CV
                    </button>
                  )}
                </div>
                {uploadError && (
                  <p style={{ color: '#ef4444', fontSize: '0.78rem', marginTop: '0.4rem' }}>
                    <AlertCircle size={13} style={{ display: 'inline', verticalAlign: 'middle', marginRight: '4px' }} />
                    {uploadError}
                  </p>
                )}
              </div>
            )}
          </div>

          <div className={styles.inputGroup}>
            <label>Preferred Programming Language</label>
            <div className={styles.langSelector}>
              {['python', 'cpp', 'javascript', 'java'].map((lang) => (
                <button
                  type="button"
                  key={lang}
                  className={`${styles.langBtn} ${preferredLang === lang ? styles.langActive : ''}`}
                  onClick={() => setPreferredLang(lang)}
                >
                  {lang === 'python' ? 'Python 3' : lang === 'cpp' ? 'C++17' : lang === 'javascript' ? 'JavaScript' : 'Java 17'}
                </button>
              ))}
            </div>
          </div>

          <button type="submit" className={styles.startBtn} disabled={uploadingCv}>
            {uploadingCv ? 'Processing CV...' : (selectedTrack === 'cv_grill' ? 'Start 30-Min CV Grilling Session →' : 'Start 1-Hour Mock Interview →')}
          </button>
        </form>
      </div>
    </div>
  );
}

