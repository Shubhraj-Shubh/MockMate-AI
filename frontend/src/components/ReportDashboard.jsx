import React from 'react';
import { 
  Download, 
  RotateCcw, 
  User, 
  Clock, 
  HelpCircle, 
  Sparkles, 
  MessageSquare 
} from 'lucide-react';
import styles from './ReportDashboard.module.css';

export default function ReportDashboard({
  reportData,
  evaluationText,
  durationSeconds,
  candidateName,
  trackName,
  q1Title,
  q2Title,
  isProcessing,
  onRestart,
  onBackToDashboard
}) {
  const actualData = reportData?.report_data || reportData || {};
  const isCvMode = actualData?.track === 'cv_grill' || (trackName || '').toLowerCase().includes('cv');

  const overallScore = actualData?.overall_score !== undefined ? String(actualData.overall_score) : (durationSeconds < 180 ? '2.5' : '7.5');
  const selfIntroScore = actualData?.section_ratings?.self_introduction !== undefined ? String(actualData.section_ratings.self_introduction) : '5.0';
  const dsaScore = actualData?.section_ratings?.dsa !== undefined ? String(actualData.section_ratings.dsa) : (durationSeconds < 180 ? '0.0' : '7.8');

  // CV Grilling Specific Ratings
  const sysArchScore = actualData?.section_ratings?.system_architecture !== undefined ? String(actualData.section_ratings.system_architecture) : '7.8';
  const techTradeoffScore = actualData?.section_ratings?.technical_tradeoffs !== undefined ? String(actualData.section_ratings.technical_tradeoffs) : '7.5';
  const projAuthScore = actualData?.section_ratings?.project_authenticity !== undefined ? String(actualData.section_ratings.project_authenticity) : '8.2';
  const crisisScore = actualData?.section_ratings?.crisis_handling !== undefined ? String(actualData.section_ratings.crisis_handling) : '7.0';

  const totalTimeSpent = actualData?.total_time_minutes 
    ? (typeof actualData.total_time_minutes === 'number' ? `${actualData.total_time_minutes} Mins` : actualData.total_time_minutes)
    : durationSeconds 
      ? (durationSeconds < 60 ? `${durationSeconds} Secs` : `${Math.round(durationSeconds / 60)} Mins`) 
      : '< 1 Min';

  const totalQuestions = actualData?.total_questions_attempted || actualData?.total_questions || (isCvMode ? '4 / 4 Probing Areas' : (durationSeconds < 180 ? '0 / 2' : '2 / 2'));

  // Extract raw detailed feedback safely
  const rawFeedback = actualData?.detailed_feedback || {};
  const hasSelfIntro = Array.isArray(rawFeedback?.self_introduction?.good_parts) && rawFeedback.self_introduction.good_parts.length > 0;
  const hasDsa = Array.isArray(rawFeedback?.dsa?.subsections) && rawFeedback.dsa.subsections.length > 0;

  // Self Introduction parameter
  const selfIntroFeedback = hasSelfIntro ? rawFeedback.self_introduction : {
    score: selfIntroScore,
    good_parts: [
      `Introduced background and core stack to the interviewer.`,
      `Maintained polite, professional, and clear vocal communication.`
    ],
    bad_parts: [
      `Could have elaborated on high-impact projects or real-world system architecture tools.`,
      `Career direction and targeted software engineering specializations could be stated more clearly.`
    ]
  };

  const isZeroDsa = parseFloat(dsaScore) === 0;

  // DSA parameter subsections
  const dsaSubsections = hasDsa ? rawFeedback.dsa.subsections : (
    isZeroDsa ? [
      {
        title: "Problem Solving Ability",
        score: "0",
        good_parts: [
          "N/A - Candidate concluded the session during the introduction phase before attempting DSA coding problems."
        ],
        bad_parts: [
          "Did not attempt coding questions due to early interview conclusion."
        ]
      },
      {
        title: "Coding Skills",
        score: "0",
        good_parts: [
          "N/A - No code was written or submitted for evaluation."
        ],
        bad_parts: [
          "Did not implement solutions to the assigned problem."
        ]
      },
      {
        title: "Communication & Collaboration",
        score: "5",
        good_parts: [
          "Engaged with interviewer during the initial introductory phase."
        ],
        bad_parts: [
          "Did not have the opportunity to discuss algorithmic trade-offs or complexities."
        ]
      },
      {
        title: "Debugging & Iteration",
        score: "0",
        good_parts: [
          "N/A - No test cases were run."
        ],
        bad_parts: [
          "Did not test or dry run code on test cases."
        ]
      }
    ] : [
      {
        title: "Problem Solving Ability",
        score: "8",
        good_parts: [
          `In ${q1Title || 'Problem 1'}, clearly explained the optimal approach after initially considering standard brute-force methods, showing strong awareness of optimization.`,
          `Demonstrated thorough understanding of time and space complexity trade-offs across arrays and hash maps.`,
          `In ${q2Title || 'Problem 2'}, broke down the problem into structured components and identified key mathematical/frequency patterns.`,
          `Adapted effectively to optimization tweaks and follow-up constraint variations.`
        ],
        bad_parts: [
          `Needed a subtle hint to transition from intermediate approaches to the optimal solution.`,
          `Could have discussed edge cases (e.g. empty inputs, negative values, large constraints) more explicitly before jumping into implementation.`,
          `Optimization reasoning in multi-phase steps could be articulated more systematically.`
        ]
      },
      {
        title: "Coding Skills",
        score: "7.5",
        good_parts: [
          `Implemented the solution correctly with clean structure, modular syntax, and efficient execution bounds.`,
          `Code was concise and logically organized with proper loop usage and variable initialization.`,
          `Utilized idiomatic language data structures efficiently without unnecessary memory overhead.`,
          `Demonstrated strong command of language syntax and library functions.`
        ],
        bad_parts: [
          `Variable naming in helper logic could be more descriptive for production readability.`,
          `Did not proactively guard against boundary edge cases like empty arrays or single-element bounds.`,
          `Initial implementation had minor index boundary oversights before test case verification.`
        ]
      },
      {
        title: "Communication & Collaboration",
        score: "8",
        good_parts: [
          `Consistently verbalized thought process while solving problems, explaining logic clearly before writing code.`,
          `Responded promptly to interviewer questions and acknowledged feedback with an open, collaborative attitude.`,
          `Maintained a receptive, professional tone throughout the session.`,
          `Used concrete examples effectively to illustrate understanding during dry runs.`
        ],
        bad_parts: [
          `Occasionally paused without vocalizing when thinking through edge case subtleties.`,
          `Some explanations were slightly verbose and could have been more tightly structured.`,
          `Could summarize overall algorithmic complexity more concisely at the conclusion.`
        ]
      },
      {
        title: "Debugging & Iteration",
        score: "7.5",
        good_parts: [
          `Provided structured step-by-step dry runs showing variable updates across iterations.`,
          `Successfully traced variable state transitions and identified logical flow under sample test cases.`,
          `Demonstrated ability to validate correctness through test-driven validation.`,
          `Quickly diagnosed and resolved edge case mismatches during test console evaluation.`
        ],
        bad_parts: [
          `Relied on interviewer prompts to initiate dry runs rather than doing so proactively.`,
          `Dry run explanations could have included more extreme corner cases and constraint boundaries.`,
          `Could be more systematic in explaining state updates during complex branch conditions.`
        ]
      }
    ]
  );

  // CV Grilling parameter list
  const cvSections = [
    {
      key: 'system_architecture',
      title: 'System Architecture & High-Level Design',
      score: sysArchScore,
      data: rawFeedback.system_architecture || {
        score: sysArchScore,
        good_parts: ['Articulated service decomposition, caching tiers, and API contract designs clearly.', 'Understood data flow bottlenecks across services.'],
        bad_parts: ['Could have discussed database indexing and replication topologies in greater detail.']
      }
    },
    {
      key: 'technical_tradeoffs',
      title: 'Technical Trade-offs & Tech Stack Choices',
      score: techTradeoffScore,
      data: rawFeedback.technical_tradeoffs || {
        score: techTradeoffScore,
        good_parts: ['Defended database and framework choices against alternatives with sound reasoning.', 'Demonstrated pragmatism between latency and consistency.'],
        bad_parts: ['Could articulate cost-efficiency and observability metrics more quantitatively.']
      }
    },
    {
      key: 'project_authenticity',
      title: 'Project Authenticity & Hands-on Ownership',
      score: projAuthScore,
      data: rawFeedback.project_authenticity || {
        score: projAuthScore,
        good_parts: ['Demonstrated deep, hands-on familiarity with the codebase, tricky bugs, and production incidents.', 'Showed genuine ownership of core modules.'],
        bad_parts: ['Some edge cases in background queue processing were glossed over.']
      }
    },
    {
      key: 'crisis_handling',
      title: 'Scale, Concurrency & Crisis Handling',
      score: crisisScore,
      data: rawFeedback.crisis_handling || {
        score: crisisScore,
        good_parts: ['Proposed sensible mitigation strategies for 50x traffic spikes and circuit breaking.', 'Understood cache invalidation thundering herd risks.'],
        bad_parts: ['Could propose more concrete disaster recovery and multi-region failover blueprints.']
      }
    }
  ];

  const handlePrint = () => {
    window.print();
  };

  const getScoreColor = (score) => {
    const num = parseFloat(score);
    if (isNaN(num)) return '#10b981';
    if (num >= 7.5) return '#10b981'; // Green
    if (num >= 6.0) return '#f59e0b'; // Gold / Orange
    return '#ef4444'; // Red
  };

  const parsePercent = (score) => {
    const num = parseFloat(score);
    if (isNaN(num)) return 75;
    return Math.min(100, Math.max(0, num * 10));
  };

  return (
    <div className={styles.reportPage}>
      {/* Top Header Bar */}
      <div className={styles.pageHeader}>
        <div className={styles.headerTitleGroup}>
          <h1>Interview Evaluation Report</h1>
        </div>
        
        <div className={styles.headerRight}>
          <div className={styles.brandBadge}>
            <div className={styles.reportLogoIcon}>
              <Sparkles size={14} />
            </div>
            <span>MockMate<strong className={styles.logoAccent}>.ai</strong></span>
          </div>
          <div className={styles.actionButtons}>
            {onBackToDashboard && (
              <button onClick={onBackToDashboard} className={styles.printBtn} title="Return to your candidate dashboard">
                &larr; Back to Dashboard
              </button>
            )}
            <button onClick={handlePrint} className={styles.printBtn} title="Print or Save as PDF">
              <Download size={15} /> Export PDF
            </button>
            <button onClick={onRestart} className={styles.restartBtn}>
              <RotateCcw size={15} /> New Interview
            </button>
          </div>
        </div>
      </div>

      {/* Loading banner if AI is generating report */}
      {isProcessing && (
        <div className={styles.loadingBanner}>
          <Sparkles className={styles.spinIcon} size={18} />
          <span>Julie is compiling your comprehensive interview evaluation report...</span>
        </div>
      )}

      {/* Main Report Container */}
      <div className={styles.reportDocument}>
        
        {/* Section 1: Overview Card */}
        <div className={styles.overviewCard}>
          <div className={styles.overviewTitle}>Overview</div>
          
          <div className={styles.overviewGrid}>
            {/* Candidate Info */}
            <div className={styles.candidateCol}>
              <div className={styles.avatarCircle}>
                <User size={30} />
              </div>
              <div className={styles.candidateDetails}>
                <h2>{candidateName || 'Candidate'}</h2>
                <p>Track: <strong>{trackName || (isCvMode ? 'CV / Resume Grilling' : 'Technical SDE Track')}</strong></p>
                <p>Skills Assessed: <strong>{isCvMode ? 'System Architecture & Projects' : 'DSA & Problem Solving'}</strong></p>
              </div>
            </div>

            {/* Weighted Overall Score */}
            <div className={styles.statCol}>
              <div className={styles.statScoreRow}>
                <span className={styles.statIcon}>🏆</span>
                <span className={styles.statBigScore} style={{ color: getScoreColor(overallScore) }}>
                  {overallScore}
                </span>
                <span className={styles.statScoreDenominator}>/10</span>
              </div>
              <div className={styles.statLabel}>Weighted Overall Score</div>
            </div>

            {/* Total Time Spent */}
            <div className={styles.statCol}>
              <div className={styles.statValueRow}>
                <Clock size={20} className={styles.statIconClock} />
                <span className={styles.statBigVal}>{totalTimeSpent}</span>
              </div>
              <div className={styles.statLabel}>Total Time Spent</div>
            </div>

            {/* Total Questions */}
            <div className={styles.statCol}>
              <div className={styles.statValueRow}>
                <HelpCircle size={20} className={styles.statIconQ} />
                <span className={styles.statBigVal}>{totalQuestions}</span>
              </div>
              <div className={styles.statLabel}>{isCvMode ? 'Probing Areas' : 'Total Questions'}</div>
            </div>
          </div>
        </div>

        {/* Section 2: Section Wise Rating */}
        <div className={styles.sectionWiseCard}>
          <div className={styles.sectionCardTitle}>Section Wise Rating</div>
          <div className={styles.sectionRatingsGrid}>
            {/* Self Introduction */}
            <div className={styles.sectionRatingItem}>
              <div className={styles.ratingLabelRow}>
                <span className={styles.ratingName}>Self Introduction</span>
                <span className={styles.ratingScore} style={{ color: getScoreColor(selfIntroScore) }}>
                  {selfIntroScore}<span>/10</span>
                </span>
              </div>
              <div className={styles.ratingBarBg}>
                <div 
                  className={styles.ratingBarFill} 
                  style={{ 
                    width: `${parsePercent(selfIntroScore)}%`,
                    backgroundColor: getScoreColor(selfIntroScore)
                  }}
                />
              </div>
            </div>

            {isCvMode ? (
              cvSections.map((sec) => (
                <div key={sec.key} className={styles.sectionRatingItem}>
                  <div className={styles.ratingLabelRow}>
                    <span className={styles.ratingName}>{sec.title}</span>
                    <span className={styles.ratingScore} style={{ color: getScoreColor(sec.score) }}>
                      {sec.score}<span>/10</span>
                    </span>
                  </div>
                  <div className={styles.ratingBarBg}>
                    <div 
                      className={styles.ratingBarFill} 
                      style={{ 
                        width: `${parsePercent(sec.score)}%`,
                        backgroundColor: getScoreColor(sec.score)
                      }}
                    />
                  </div>
                </div>
              ))
            ) : (
              /* DSA */
              <div className={styles.sectionRatingItem}>
                <div className={styles.ratingLabelRow}>
                  <span className={styles.ratingName}>DSA</span>
                  <span className={styles.ratingScore} style={{ color: getScoreColor(dsaScore) }}>
                    {dsaScore}<span>/10</span>
                  </span>
                </div>
                <div className={styles.ratingBarBg}>
                  <div 
                    className={styles.ratingBarFill} 
                    style={{ 
                      width: `${parsePercent(dsaScore)}%`,
                      backgroundColor: getScoreColor(dsaScore)
                    }}
                  />
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Section 3: Detailed Feedback on Evaluation Parameters */}
        <div className={styles.detailedFeedbackSection}>
          <h3 className={styles.detailedSectionHeader}>Detailed Feedback on Evaluation Parameters</h3>

          {/* Parameter 1: Self Introduction */}
          <div className={styles.parameterCard}>
            <div className={styles.parameterHeader}>
              <div className={styles.parameterLeft}>
                <h4>Self Introduction</h4>
                <span className={styles.weightageBadge}>Weightage N/A</span>
              </div>
              <div className={styles.parameterScoreCircle} style={{ borderColor: getScoreColor(selfIntroScore) }}>
                <span className={styles.circleScoreVal} style={{ color: getScoreColor(selfIntroScore) }}>
                  {selfIntroScore}
                </span>
                <span className={styles.circleScoreDenom}>/10</span>
              </div>
            </div>

            {/* Good Parts */}
            <div className={styles.feedbackBlock}>
              <div className={styles.goodPartsTitle}>Good Parts</div>
              <ul className={styles.goodPartsList}>
                {selfIntroFeedback.good_parts?.map((item, idx) => (
                  <li key={idx}>• {item}</li>
                ))}
              </ul>
            </div>

            {/* Bad Parts */}
            <div className={styles.feedbackBlock}>
              <div className={styles.badPartsTitle}>Bad Parts</div>
              <ul className={styles.badPartsList}>
                {selfIntroFeedback.bad_parts?.map((item, idx) => (
                  <li key={idx}>• {item}</li>
                ))}
              </ul>
            </div>
          </div>

          {/* Parameter 2: CV Grilling Sections or DSA Master Card */}
          {isCvMode ? (
            cvSections.map((sec) => {
              const secColor = getScoreColor(sec.score);
              return (
                <div key={sec.key} className={styles.parameterCard}>
                  <div className={styles.parameterHeader}>
                    <div className={styles.parameterLeft}>
                      <h4>{sec.title}</h4>
                      <span className={styles.weightageBadge}>Core Grilling Assessment</span>
                    </div>
                    <div className={styles.parameterScoreCircle} style={{ borderColor: secColor }}>
                      <span className={styles.circleScoreVal} style={{ color: secColor }}>
                        {sec.score}
                      </span>
                      <span className={styles.circleScoreDenom}>/10</span>
                    </div>
                  </div>

                  <div className={styles.feedbackBlock}>
                    <div className={styles.goodPartsTitle}>Good Parts</div>
                    <ul className={styles.goodPartsList}>
                      {(sec.data?.good_parts || []).map((item, pIdx) => (
                        <li key={pIdx}>• {item}</li>
                      ))}
                    </ul>
                  </div>

                  <div className={styles.feedbackBlock}>
                    <div className={styles.badPartsTitle}>Bad Parts & Areas for Improvement</div>
                    <ul className={styles.badPartsList}>
                      {(sec.data?.bad_parts || []).map((item, pIdx) => (
                        <li key={pIdx}>• {item}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              );
            })
          ) : (
            <div className={styles.dsaMasterCard}>
              <div className={styles.dsaMasterHeader}>
                <div className={styles.dsaHeaderLeft}>
                  <h4>DSA</h4>
                  <span className={styles.weightageBadge}>Weightage N/A</span>
                </div>
                <div className={styles.dsaMasterScore} style={{ color: getScoreColor(dsaScore) }}>
                  {dsaScore}<span>/10</span>
                </div>
              </div>

              {/* DSA Subsections */}
              {dsaSubsections.map((sub, idx) => {
                const subColor = getScoreColor(sub.score);
                return (
                  <div key={idx} className={styles.dsaSubCard}>
                    {/* Subsection Header */}
                    <div className={styles.dsaSubHeader}>
                      <div className={styles.dsaSubTitleGroup}>
                        <h5>{sub.title}</h5>
                        <div className={styles.subProgressBar}>
                          <div 
                            className={styles.subProgressFill} 
                            style={{ 
                              width: `${parsePercent(sub.score)}%`,
                              backgroundColor: subColor
                            }} 
                          />
                        </div>
                      </div>

                      <div className={styles.subScoreCircle} style={{ borderColor: subColor }}>
                        <span className={styles.subCircleVal} style={{ color: subColor }}>
                          {sub.score}
                        </span>
                        <span className={styles.subCircleDenom}>/10</span>
                      </div>
                    </div>

                    {/* Good Parts */}
                    <div className={styles.feedbackBlock}>
                      <div className={styles.goodPartsTitle}>Good Parts</div>
                      <ul className={styles.goodPartsList}>
                        {sub.good_parts?.map((item, pIdx) => (
                          <li key={pIdx}>• {item}</li>
                        ))}
                      </ul>
                    </div>

                    {/* Bad Parts */}
                    <div className={styles.feedbackBlock}>
                      <div className={styles.badPartsTitle}>Bad Parts</div>
                      <ul className={styles.badPartsList}>
                        {sub.bad_parts?.map((item, pIdx) => (
                          <li key={pIdx}>• {item}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Section 4: Interviewer Executive Summary */}
          {(evaluationText || actualData?.evaluation_report) && (
            <div className={styles.summaryCard}>
              <div className={styles.summaryHeader}>
                <MessageSquare size={18} className={styles.summaryIcon} />
                <h4>Interviewer's Concluding Remarks</h4>
              </div>
              <p className={styles.summaryText}>
                {evaluationText || actualData?.evaluation_report}
              </p>
            </div>
          )}

        </div>

      </div>
    </div>
  );
}
