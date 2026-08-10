import { useState } from 'react';
import { Play, Send, CheckCircle2, XCircle, Clock, Terminal, ChevronDown, ChevronUp } from 'lucide-react';
import styles from './TestConsole.module.css';

export default function TestConsole({
  onRunCode,
  onSubmitSolution,
  isRunning,
  isSubmitting,
  testResults,
  isEditorEnabled
}) {
  const [activeTab, setActiveTab] = useState(0);
  const [isExpanded, setIsExpanded] = useState(true);

  const results = testResults?.results || [];
  const currentTest = results[activeTab] || results[0];

  return (
    <div className={`${styles.consoleContainer} ${isExpanded ? styles.expanded : styles.collapsed}`}>
      <div className={styles.header}>
        <div className={styles.title} onClick={() => setIsExpanded(!isExpanded)}>
          <Terminal size={16} />
          <span>Test Console</span>
          {testResults && (
            <span className={`${styles.summaryBadge} ${testResults.all_passed ? styles.badgeSuccess : styles.badgeFail}`}>
              {testResults.total_passed}/{testResults.total_tests} Passed
            </span>
          )}
          {isExpanded ? <ChevronDown size={16} /> : <ChevronUp size={16} />}
        </div>

        <div className={styles.actions}>
          <button
            className={styles.runBtn}
            onClick={onRunCode}
            disabled={!isEditorEnabled || isRunning || isSubmitting}
            title="Run code against sample test cases"
          >
            <Play size={14} />
            {isRunning ? 'Running...' : 'Run Code'}
          </button>
          
          <button
            className={styles.submitBtn}
            onClick={onSubmitSolution}
            disabled={!isEditorEnabled || isRunning || isSubmitting}
            title="Submit code against all test cases"
          >
            <Send size={14} />
            {isSubmitting ? 'Evaluating...' : 'Submit Solution'}
          </button>
        </div>
      </div>

      {isExpanded && (
        <div className={styles.body}>
          {isRunning || isSubmitting ? (
            <div className={styles.loadingState}>
              <div className={styles.spinner}></div>
              <span>Executing test cases in isolated sandbox...</span>
            </div>
          ) : results.length > 0 ? (
            <div className={styles.resultsLayout}>
              {/* Test Case Tabs */}
              <div className={styles.tabsList}>
                {results.map((r, idx) => (
                  <button
                    key={r.test_id}
                    className={`${styles.tabBtn} ${activeTab === idx ? styles.tabActive : ''}`}
                    onClick={() => setActiveTab(idx)}
                  >
                    {r.passed ? (
                      <CheckCircle2 size={14} className={styles.passIcon} />
                    ) : (
                      <XCircle size={14} className={styles.failIcon} />
                    )}
                    <span>Case {idx + 1}</span>
                  </button>
                ))}
              </div>

              {/* Selected Test Case Details */}
              {currentTest && (
                <div className={styles.details}>
                  <div className={styles.metaRow}>
                    <div className={styles.statusLabel}>
                      Status:{' '}
                      <strong className={currentTest.passed ? styles.textPass : styles.textFail}>
                        {currentTest.passed ? 'Accepted' : 'Wrong Answer / Error'}
                      </strong>
                    </div>
                    <div className={styles.timeLabel}>
                      <Clock size={12} /> {currentTest.execution_time_ms} ms
                    </div>
                  </div>

                  <div className={styles.dataBlock}>
                    <label>Input</label>
                    <pre>{currentTest.input}</pre>
                  </div>

                  <div className={styles.dataBlock}>
                    <label>Expected Output</label>
                    <pre>{currentTest.expected_output}</pre>
                  </div>

                  <div className={styles.dataBlock}>
                    <label>Your Output</label>
                    <pre className={currentTest.passed ? styles.outputPass : styles.outputFail}>
                      {currentTest.actual_output || 'No output'}
                    </pre>
                  </div>

                  {currentTest.error && (
                    <div className={styles.errorBlock}>
                      <label>Error Details</label>
                      <pre>{currentTest.error}</pre>
                    </div>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div className={styles.emptyState}>
              Click <strong>"Run Code"</strong> to test your solution against example test cases.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
