import { useState, useRef, useEffect } from 'react';
import { FaceDetector, FilesetResolver } from '@mediapipe/tasks-vision';
import Editor from '@monaco-editor/react';
import {
  Mic, MicOff, Video, VideoOff, Phone, Lock, Code, CheckCircle,
  Circle, Send, Play, Sparkles, User, LogIn, LogOut, BarChart2, ArrowLeft,
  Maximize2, Minimize2, PanelLeftClose, PanelLeftOpen, Columns, FileText
} from 'lucide-react';
import SetupModal from './components/SetupModal';
import TestConsole from './components/TestConsole';
import ReportDashboard from './components/ReportDashboard';
import AuthModal from './components/AuthModal';
import PastInterviewsModal from './components/PastInterviewsModal';
import AuthScreen from './components/AuthScreen';
import HomeDashboard from './components/HomeDashboard';
import { useAuth } from './context/AuthContext';
import { API_BASE_URL } from './config';
import styles from './App.module.css';

const INTERVIEW_STAGES = [
  { id: 'Intro', label: '1. Intro' },
  { id: 'P1', label: '2. Problem 1' },
  { id: 'P1_Complexity', label: '3. Q1 Big-O' },
  { id: 'P2', label: '4. Adaptive Q2' },
  { id: 'P2_Followup', label: '5. Q2 Follow-up' },
  { id: 'Wrap-up', label: '6. Evaluation' }
];

const CV_INTERVIEW_STAGES = [
  { id: 'CV_Intro', label: '1. CV Review' },
  { id: 'CV_Flagship', label: '2. Flagship Project' },
  { id: 'CV_DeepDive', label: '3. Architecture & Code' },
  { id: 'CV_Tradeoffs', label: '4. Scaling & Trade-offs' },
  { id: 'CV_Wrapup', label: '5. Evaluation' }
];

const DEFAULT_STARTER_CODES = {
  python: `def twoSum(nums: list[int], target: int) -> list[int]:\n    # Write your solution here\n    pass\n`,
  cpp: `#include <vector>\nusing namespace std;\n\nclass Solution {\npublic:\n    vector<int> twoSum(vector<int>& nums, int target) {\n        // Write your solution here\n        return {};\n    }\n};\n`,
  javascript: `function twoSum(nums, target) {\n    // Write your solution here\n    return [];\n}\n`,
  java: `import java.util.*;\n\nclass Solution {\n    public int[] twoSum(int[] nums, int target) {\n        // Write your solution here\n        return new int[]{};\n    }\n}\n`
};

const CV_DEFAULT_STARTER_CODES = {
  javascript: '// System Architecture & Technical Discussion Scratchpad\n// Use this space to sketch data flows, schemas, or pseudocode if asked.\n',
  java: '// System Architecture & Technical Discussion Scratchpad\n// Use this space to sketch data flows, schemas, or pseudocode if asked.\n'
};

function App() {
  const { user, logout, isAuthenticated, loading } = useAuth();
  const [viewMode, setViewMode] = useState('dashboard'); // 'dashboard' | 'interview' | 'report'

  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [isHistoryModalOpen, setIsHistoryModalOpen] = useState(false);

  const [isSetupOpen, setIsSetupOpen] = useState(false);
  const [candidateName, setCandidateName] = useState('Candidate');
  const [interviewerName, setInterviewerName] = useState('Sanya');
  const [track, setTrack] = useState('medium');
  const [trackName, setTrackName] = useState('Medium Tier (1 Medium + 1 Hard)');
  const [language, setLanguage] = useState('python');
  const [code, setCode] = useState('class Solution:\n    def twoSum(self, nums: list[int], target: int) -> list[int]:\n        # Write your solution here\n        return []');
  const [parsedCv, setParsedCv] = useState(null);

  const [isRecording, setIsRecording] = useState(false);
  const [isVideoOn, setIsVideoOn] = useState(true);
  const [isEditorEnabled, setIsEditorEnabled] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isAiSpeaking, setIsAiSpeaking] = useState(false);
  const [subtitles, setSubtitles] = useState('');
  const [currentPhase, setCurrentPhase] = useState('Intro');

  const [textInput, setTextInput] = useState('');
  const [activeProblemId, setActiveProblemId] = useState('two_sum');
  const [problemHtml, setProblemHtml] = useState(null);
  const [testResults, setTestResults] = useState(null);
  const [isRunningCode, setIsRunningCode] = useState(false);
  const [isSubmittingCode, setIsSubmittingCode] = useState(false);

  const [timeLeft, setTimeLeft] = useState(3600); // Timer in seconds (1 hour default)
  const [isInterviewEnded, setIsInterviewEnded] = useState(false);
  const [evaluationReport, setEvaluationReport] = useState('');
  const [reportData, setReportData] = useState(null);
  const [durationSeconds, setDurationSeconds] = useState(0);

  // Proctoring States
  const [isInterviewPaused, setIsInterviewPaused] = useState(false);
  const faceDetectorRef = useRef(null);
  const lastFaceTimeRef = useRef(Date.now());

  // Flexible Layout State (Question Tab & Code Tab expand/collapse/drag)
  const [questionWidth, setQuestionWidth] = useState(40); // 40% default width for Question panel
  const [isQuestionCollapsed, setIsQuestionCollapsed] = useState(false);
  const [isQuestionExpanded, setIsQuestionExpanded] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const workspaceRef = useRef(null);

  const handleMouseDown = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  useEffect(() => {
    const handleMouseMove = (e) => {
      if (!isDragging || !workspaceRef.current) return;
      const rect = workspaceRef.current.getBoundingClientRect();
      const newWidth = ((e.clientX - rect.left) / rect.width) * 100;
      if (newWidth >= 18 && newWidth <= 82) {
        setQuestionWidth(newWidth);
      }
    };

    const handleMouseUp = () => {
      if (isDragging) {
        setIsDragging(false);
      }
    };

    if (isDragging) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    } else {
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    }

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isDragging]);

  const toggleQuestionCollapsed = () => {
    setIsQuestionExpanded(false);
    setIsQuestionCollapsed(prev => !prev);
  };

  const toggleQuestionExpanded = () => {
    setIsQuestionCollapsed(false);
    setIsQuestionExpanded(prev => !prev);
  };

  const toggleEditorExpanded = () => {
    setIsQuestionExpanded(false);
    setIsQuestionCollapsed(prev => !prev);
  };

  // Live Dynamic Network Strength Measurement
  const [networkSpeed, setNetworkSpeed] = useState({
    label: 'Connecting...',
    rtt: 0,
    mbps: 0,
    status: 'good'
  });

  useEffect(() => {
    let isMounted = true;

    const measureNetwork = async () => {
      try {
        const start = performance.now();
        // Fetch test payload from backend with cache-buster to compute true live round-trip latency & throughput
        const res = await fetch(`${API_BASE_URL}/api/network-ping?size_kb=32&_t=${Date.now()}`, {
          method: 'GET',
          cache: 'no-store'
        });
        const durationMs = Math.max(1, Math.round(performance.now() - start));

        if (res.ok) {
          const data = await res.json();
          const bytes = (data?.bytes || 32768) + 350; // include HTTP header frame overhead
          // True throughput in Mbps: (bytes * 8) / (seconds * 1,000,000)
          const measuredMbps = Number(((bytes * 8) / ((durationMs / 1000) * 1000000)).toFixed(1));

          let status = 'good';
          if (durationMs > 250) {
            status = 'poor';
          } else if (durationMs > 90) {
            status = 'fair';
          }

          // Dynamic display showing live latency and speed (e.g. "12 ms • 28.4 Mbps" or "18 ms")
          const speedDisplay = measuredMbps > 0 ? `${durationMs} ms • ${measuredMbps} Mbps` : `${durationMs} ms`;

          if (isMounted) {
            setNetworkSpeed({
              label: speedDisplay,
              rtt: durationMs,
              mbps: measuredMbps,
              status
            });
          }
        } else {
          if (isMounted) {
            setNetworkSpeed({
              label: `${durationMs} ms (Fair)`,
              rtt: durationMs,
              mbps: 0,
              status: 'fair'
            });
          }
        }
      } catch (err) {
        if (isMounted) {
          setNetworkSpeed({
            label: 'Offline',
            rtt: 0,
            mbps: 0,
            status: 'poor'
          });
        }
      }
    };

    measureNetwork();
    const interval = setInterval(measureNetwork, 2500);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const videoRef = useRef(null);
  const recognitionRef = useRef(null);
  const sessionIdRef = useRef(Math.random().toString(36).substring(7));
  const preferredVoiceRef = useRef(null);

  const transcriptBufferRef = useRef('');
  const interimTranscriptRef = useRef('');
  const isRecordingRef = useRef(false);
  const loadedProblemIdRef = useRef(null);
  const codePerLangRef = useRef({});
  const allStarterCodesRef = useRef({});

  const handleSelectPastReport = (pastReport) => {
    setReportData(pastReport);
    setEvaluationReport(pastReport.evaluation_report || '');
    setDurationSeconds(pastReport.duration_seconds || 0);
    setCandidateName(pastReport.candidate_name || 'Candidate');
    setTrackName(pastReport.track_name || 'Technical Track');
    setIsInterviewEnded(true);
    setViewMode('report');
  };

  const startInterviewSession = async (config) => {
    const chosenLang = config.language || 'python';
    const isCvMode = config.track === 'cv_grill';

    setCandidateName(config.candidateName);
    setTrack(config.track);
    setLanguage(chosenLang);
    setIsSetupOpen(false);
    setIsInterviewEnded(false);
    setViewMode('interview');
    setTimeLeft(isCvMode ? 1800 : 3600);
    setCurrentPhase(isCvMode ? 'CV Intro' : 'Intro');

    if (config.cvData?.parsed_data) {
      setParsedCv(config.cvData.parsed_data);
    } else {
      setParsedCv(null);
    }

    codePerLangRef.current = {};
    allStarterCodesRef.current = {};
    const defaultCodes = isCvMode ? CV_DEFAULT_STARTER_CODES : DEFAULT_STARTER_CODES;
    setCode(defaultCodes[chosenLang] || defaultCodes.python);

    try {
      const formData = new FormData();
      formData.append('session_id', sessionIdRef.current);
      formData.append('track', config.track);
      formData.append('candidate_name', config.candidateName);
      formData.append('resume_summary', config.resumeBio);
      formData.append('interviewer_name', config.interviewerName || 'Sanya');
      setInterviewerName(config.interviewerName || 'Sanya');
      formData.append('user_email', config.userEmail || user?.email || '');

      const res = await fetch(`${API_BASE_URL}/api/setup-interview`, {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (data.track_name) {
        setTrackName(data.track_name);
      }
      if (data.parsed_cv) {
        setParsedCv(data.parsed_cv);
      }
      if (data.duration_seconds) {
        setTimeLeft(data.duration_seconds);
      }
      if (data.q1_id) {
        setActiveProblemId(data.q1_id);
      }
      if (data.q1_starter_codes) {
        allStarterCodesRef.current = data.q1_starter_codes;
        const initialCode = data.q1_starter_codes[chosenLang] || data.q1_starter_codes['python'] || defaultCodes[chosenLang];
        if (initialCode) {
          setCode(initialCode);
          codePerLangRef.current[chosenLang] = initialCode;
        }
      }
    } catch (e) {
      console.error('Setup interview error:', e);
    }

    // Trigger opening greeting from interviewer
    await handleUserAudioSubmission('', false, true);
  };


  // MediaPipe Face Detector Initialization
  useEffect(() => {
    async function initializeFaceDetector() {
      try {
        const vision = await FilesetResolver.forVisionTasks(
          "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision/wasm"
        );
        const detector = await FaceDetector.createFromOptions(vision, {
          baseOptions: {
            modelAssetPath: "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite",
            delegate: "CPU"
          },
          runningMode: "VIDEO"
        });
        faceDetectorRef.current = detector;
      } catch (err) {
        console.error("FaceDetector init error:", err);
      }
    }
    initializeFaceDetector();
  }, []);

  // MediaPipe Detection Loop
  useEffect(() => {
    if (viewMode !== 'interview') return;

    let requestAnimationFrameId;
    let lastVideoTime = -1;

    const detectFace = () => {
      if (videoRef.current && faceDetectorRef.current && videoRef.current.readyState >= 2 && videoRef.current.videoWidth > 0) {
        const startTimeMs = performance.now();
        if (videoRef.current.currentTime !== lastVideoTime) {
          lastVideoTime = videoRef.current.currentTime;
          try {
            const detections = faceDetectorRef.current.detectForVideo(videoRef.current, startTimeMs);
            
            if (detections.detections && detections.detections.length > 0) {
              lastFaceTimeRef.current = Date.now();
              if (isInterviewPaused) {
                setIsInterviewPaused(false);
              }
            } else {
              if (Date.now() - lastFaceTimeRef.current > 5000) {
                if (!isInterviewPaused) {
                  setIsInterviewPaused(true);
                  if (isRecordingRef.current) {
                    try {
                      recognitionRef.current?.stop();
                      isRecordingRef.current = false;
                      setIsRecording(false);
                    } catch (e) {}
                  }
                }
              }
            }
          } catch(e) {
            console.error("Detection error:", e);
          }
        }
      } else {
        // If the camera hasn't loaded yet, keep resetting the timer so we don't instantly auto-pause!
        lastFaceTimeRef.current = Date.now();
      }
      requestAnimationFrameId = requestAnimationFrame(detectFace);
    };

    detectFace();

    return () => {
      if (requestAnimationFrameId) {
        cancelAnimationFrame(requestAnimationFrameId);
      }
    };
  }, [viewMode, isInterviewPaused]);

  // Camera setup on entering interview
  useEffect(() => {
    if (viewMode !== 'interview') return;

    async function setupCamera() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
      } catch (err) {
        console.error('Error accessing media devices:', err);
      }
    }
    setupCamera();
  }, [viewMode]);

  // Speech Recognition setup
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;

      recognition.onresult = (event) => {
        let currentInterim = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            transcriptBufferRef.current += event.results[i][0].transcript + ' ';
          } else {
            currentInterim += event.results[i][0].transcript;
          }
        }
        interimTranscriptRef.current = currentInterim;
        setSubtitles((transcriptBufferRef.current + ' ' + currentInterim).trim());
      };

      recognition.onerror = (event) => {
        console.error("Speech recognition error", event.error);
        if (event.error !== 'no-speech') {
          isRecordingRef.current = false;
          setIsRecording(false);
        }
      };

      recognition.onend = () => {
        if (isRecordingRef.current) {
          try {
            recognition.start();
          } catch (e) {
            console.error("Failed to restart recognition:", e);
          }
        }
      };

      recognitionRef.current = recognition;
    }

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      window.speechSynthesis.cancel();
    };
  }, []);

  // Timer countdown
  useEffect(() => {
    if (isInterviewEnded || viewMode !== 'interview') return;

    const timerId = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          clearInterval(timerId);
          handleEndInterview();
          return 0;
        }
        return prev - 1;
      });
      setDurationSeconds((d) => d + 1);
    }, 1000);

    return () => clearInterval(timerId);
  }, [isInterviewEnded, viewMode]);

  const formatTime = (seconds) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}m : ${s < 10 ? '0' : ''}${s}s`;
  };

  const handlePushToTalk = () => {
    window.speechSynthesis.cancel();
    setIsAiSpeaking(false);

    if (!recognitionRef.current) {
      alert("Speech recognition not supported in this browser. You can type in the response box below!");
      return;
    }

    if (isRecordingRef.current) {
      isRecordingRef.current = false;
      setIsRecording(false);
      try {
        recognitionRef.current.stop();
      } catch (e) { }

      const fullText = (transcriptBufferRef.current + ' ' + interimTranscriptRef.current).trim();
      transcriptBufferRef.current = '';
      interimTranscriptRef.current = '';

      if (fullText) {
        handleUserAudioSubmission(fullText);
      } else if (currentPhase === 'Intro') {
        handleUserAudioSubmission("I've introduced myself and I'm ready to begin Question 1.");
      } else if (isEditorEnabled) {
        handleUserAudioSubmission("I've written some code for this problem. Could you please review it?");
      } else {
        setSubtitles("No speech detected. Speak into your mic or type below.");
      }
    } else {
      transcriptBufferRef.current = '';
      interimTranscriptRef.current = '';
      setSubtitles('Listening... Speak now.');
      try {
        recognitionRef.current.start();
        isRecordingRef.current = true;
        setIsRecording(true);
      } catch (e) {
        console.error("Speech recognition start failed:", e);
      }
    }
  };

  const handleTextSubmit = (e) => {
    e.preventDefault();
    if (!textInput.trim() || isProcessing) return;

    window.speechSynthesis.cancel();
    setIsAiSpeaking(false);

    const message = textInput;
    setTextInput('');
    handleUserAudioSubmission(message);
  };

  const handleQuickAdvance = () => {
    if (isProcessing) return;
    window.speechSynthesis.cancel();
    setIsAiSpeaking(false);
    handleUserAudioSubmission("I am ready to begin Question 1. Please give me the first coding problem.", false, false, true);
  };

  const handleRunCode = async () => {
    if (isRunningCode || isSubmittingCode) return;
    setIsRunningCode(true);

    try {
      const res = await fetch(`${API_BASE_URL}/api/run-code`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          problem_id: activeProblemId,
          code: code,
          language: language,
          session_id: sessionIdRef.current
        })
      });
      const data = await res.json();
      setTestResults(data);
    } catch (e) {
      console.error('Run code error:', e);
      setTestResults({
        passed: 0,
        total: 0,
        results: [],
        compilation_error: 'Failed to connect to execution server.'
      });
    } finally {
      setIsRunningCode(false);
    }
  };

  const handleSubmitSolution = async () => {
    if (isRunningCode || isSubmittingCode) return;
    setIsSubmittingCode(true);

    try {
      const res = await fetch(`${API_BASE_URL}/api/submit-solution`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          problem_id: activeProblemId,
          code: code,
          language: language,
          session_id: sessionIdRef.current
        })
      });
      const data = await res.json();
      setTestResults(data);

      if (data.all_passed) {
        handleUserAudioSubmission(
          `I have submitted my code and passed all ${data.passed}/${data.total} test cases! Let's discuss time/space complexity or move to the next question.`
        );
      } else {
        handleUserAudioSubmission(
          `I submitted my code. It passed ${data.passed} out of ${data.total} test cases. There were some failing cases.`
        );
      }
    } catch (e) {
      console.error('Submit solution error:', e);
    } finally {
      setIsSubmittingCode(false);
    }
  };

  const handleLanguageChange = (e) => {
    const newLang = e.target.value;

    // Save current buffer for the language we are leaving
    codePerLangRef.current[language] = code;
    setLanguage(newLang);

    // 1. If candidate already wrote/edited code in newLang, restore it
    if (codePerLangRef.current[newLang]) {
      setCode(codePerLangRef.current[newLang]);
      return;
    }

    // 2. If problem starter code for newLang is cached locally, use it
    if (allStarterCodesRef.current && allStarterCodesRef.current[newLang]) {
      const snippet = allStarterCodesRef.current[newLang];
      setCode(snippet);
      codePerLangRef.current[newLang] = snippet;
      return;
    }

    // 3. Fetch from backend
    fetchProblemDetails(activeProblemId, newLang);
  };

  const fetchProblemDetails = async (problemId, lang) => {
    try {
      const langToFetch = lang || language;
      const res = await fetch(`${API_BASE_URL}/api/problem/${problemId || 'active'}?language=${langToFetch}&session_id=${sessionIdRef.current}`);
      if (res.ok) {
        const data = await res.json();
        if (data.html) {
          setProblemHtml(data.html);
        }
        if (data.all_starter_codes) {
          allStarterCodesRef.current = data.all_starter_codes;
        }
        if (data.starter_code) {
          setCode(data.starter_code);
          codePerLangRef.current[langToFetch] = data.starter_code;
        }
      } else {
        const fallback = DEFAULT_STARTER_CODES[langToFetch] || DEFAULT_STARTER_CODES.python;
        setCode(fallback);
      }
      setTestResults(null);
    } catch (e) {
      console.error("Fetch problem error", e);
      const fallback = DEFAULT_STARTER_CODES[lang || language] || DEFAULT_STARTER_CODES.python;
      setCode(fallback);
    }
  };

  const handleUserAudioSubmission = async (userInputText, isFinalSubmission = false, isOpeningGreeting = false, isQuickAdvance = false) => {
    setIsProcessing(true);
    setSubtitles(isOpeningGreeting ? `${interviewerName} is entering the room...` : 'Interviewer is evaluating...');

    try {
      const formData = new FormData();
      formData.append('text_input', userInputText);
      formData.append('current_code', code);
      formData.append('language', language);
      formData.append('session_id', sessionIdRef.current);
      formData.append('is_final_submission', isFinalSubmission.toString());
      formData.append('is_opening_greeting', isOpeningGreeting.toString());
      formData.append('is_quick_advance', isQuickAdvance.toString());

      const response = await fetch(`${API_BASE_URL}/api/interview-stream`, {
        method: 'POST',
        body: formData
      });

      const data = await response.json();

      if (data.active_problem_id) {
        const newProbId = data.active_problem_id;
        setActiveProblemId(newProbId);

        if (loadedProblemIdRef.current !== newProbId) {
          loadedProblemIdRef.current = newProbId;
          codePerLangRef.current = {};

          if (data.all_starter_codes) {
            allStarterCodesRef.current = data.all_starter_codes;
          }
          if (data.starter_code) {
            setCode(data.starter_code);
            codePerLangRef.current[language] = data.starter_code;
          }
          if (data.problem_html) {
            setProblemHtml(data.problem_html);
          }
          if (!data.starter_code || !data.problem_html) {
            fetchProblemDetails(newProbId, language);
          }
        }
      }

      if (data.current_phase) {
        setCurrentPhase(data.current_phase);
      }

      if (data.enable_editor !== undefined) {
        setIsEditorEnabled(data.enable_editor);
      }

      if (data.interview_ended || data.current_phase === 'Wrap-up' || data.current_phase === 'Completed' || data.current_phase === 'CV Wrap-up') {
        setIsInterviewEnded(true);
        setViewMode('report');
        setEvaluationReport(data.evaluation_report || '');
        setReportData(data.report_data || data);

        if (recognitionRef.current) {
          recognitionRef.current.stop();
        }
        setIsRecording(false);

        if (videoRef.current && videoRef.current.srcObject) {
          const tracks = videoRef.current.srcObject.getTracks();
          tracks.forEach(track => track.stop());
        }
      }

      const spokenText = data.interviewer_response || data.ai_response || '';
      if (spokenText) {
        setSubtitles(spokenText);
        playSpeech(spokenText);
      }

    } catch (err) {
      console.error("Interview API error:", err);
      setSubtitles("Connection glitch. Please try again.");
    } finally {
      setIsProcessing(false);
    }
  };

  const playSpeech = (text) => {
    if (!('speechSynthesis' in window)) return;

    window.speechSynthesis.cancel();
    const cleanText = text.replace(/[*_#`]/g, '');
    const utterance = new SpeechSynthesisUtterance(cleanText);

    const voices = window.speechSynthesis.getVoices();

    // Prioritize high-gain, crystal clear, confident female voices
    const googleFemale = voices.find(v =>
      (v.name.includes('Google') || v.name.includes('Natural')) &&
      (v.name.includes('US English') || v.name.includes('UK English Female') || v.name.includes('Female') || v.name.includes('Jenny') || v.name.includes('Aria') || v.name.includes('Sonia') || v.name.includes('Neerja'))
    );
    const appleFemale = voices.find(v =>
      (v.name.includes('Samantha') || v.name.includes('Karen') || v.name.includes('Victoria') || v.name.includes('Ava') || v.name.includes('Serena') || v.name.includes('Zoe') || v.name.includes('Tessa')) &&
      !v.name.toLowerCase().includes('male')
    );
    const standardFemale = voices.find(v => {
      const name = v.name.toLowerCase();
      const isEnglish = v.lang.includes('en');
      return isEnglish && (
        name.includes('female') || name.includes('woman') || name.includes('samantha') || name.includes('karen') || name.includes('victoria') || name.includes('zira') || name.includes('veena') || name.includes('neerja')
      );
    });
    const anyNonMale = voices.find(v => {
      const name = v.name.toLowerCase();
      const isEnglish = v.lang.includes('en');
      const isMale = name.includes('male') || name.includes('guy') || name.includes('david') || name.includes('george') || name.includes('mark') || name.includes('prabhat') || name.includes('rishi') || name.includes('ravi') || name.includes('daniel') || name.includes('alex') || name.includes('fred');
      return isEnglish && !isMale;
    });

    utterance.voice = googleFemale || appleFemale || standardFemale || anyNonMale || voices[0];
    utterance.volume = 1.0;
    utterance.rate = 1.0;
    utterance.pitch = 0.98; // Confident, clear resonance

    utterance.onstart = () => setIsAiSpeaking(true);
    utterance.onend = () => setIsAiSpeaking(false);
    utterance.onerror = () => setIsAiSpeaking(false);

    window.speechSynthesis.speak(utterance);
  };

  const handleEndInterview = () => {
    if (isInterviewEnded) return;
    setIsInterviewEnded(true);
    setViewMode('report');

    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }
    setIsRecording(false);

    if (videoRef.current && videoRef.current.srcObject) {
      const tracks = videoRef.current.srcObject.getTracks();
      tracks.forEach(track => track.stop());
    }

    handleUserAudioSubmission("I would like to end the interview now. Please evaluate my overall performance.", true);
  };

  const handleRestart = () => {
    sessionIdRef.current = Math.random().toString(36).substring(7);
    loadedProblemIdRef.current = null;
    setIsInterviewEnded(false);
    setEvaluationReport('');
    setReportData(null);
    setCurrentPhase('Intro');
    setTimeLeft(3600);
    setDurationSeconds(0);
    setProblemHtml(null);
    setIsSetupOpen(true);
    setViewMode('dashboard');
  };

  const handleExitToDashboard = () => {
    const confirmExit = window.confirm("Are you sure you want to exit to the Candidate Dashboard? Your current session will end.");
    if (!confirmExit) return;

    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }
    setIsRecording(false);

    if (videoRef.current && videoRef.current.srcObject) {
      const tracks = videoRef.current.srcObject.getTracks();
      tracks.forEach(track => track.stop());
    }

    window.speechSynthesis.cancel();
    setIsAiSpeaking(false);
    setViewMode('dashboard');
  };

  const isCvGrill = track === 'cv_grill';
  const activeStages = isCvGrill ? CV_INTERVIEW_STAGES : INTERVIEW_STAGES;

  const getStageIndex = (phaseName) => {
    if (isCvGrill) {
      if (!phaseName || phaseName.includes('Intro')) return 0;
      if (phaseName.includes('Project 1') || phaseName.includes('Deep Dive')) return 1;
      if (phaseName.includes('Stress') || phaseName.includes('Scale')) return 2;
      if (phaseName.includes('Project 2') || phaseName.includes('Verification')) return 3;
      if (phaseName.includes('Wrap') || phaseName.includes('Completed')) return 4;
      return 0;
    }
    if (!phaseName || phaseName === 'Intro') return 0;
    if (phaseName === 'P1 Approach' || phaseName === 'P1 Coding' || phaseName === 'Question 1') return 1;
    if (phaseName === 'P1 Complexity' || phaseName === 'Question 1 Follow-up') return 2;
    if (phaseName === 'P2 Approach' || phaseName === 'P2 Coding' || phaseName === 'Question 2') return 3;
    if (phaseName === 'P2 Followup' || phaseName === 'Question 2 Follow-up') return 4;
    if (phaseName === 'Wrap-up') return 5;
    return 0;
  };

  const currentStageIdx = getStageIndex(currentPhase);

  // 1. Loading State
  if (loading) {
    return (
      <div style={{ minHeight: '100vh', background: '#0a0f1d', color: '#f3f4f6', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'sans-serif' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ width: '40px', height: '40px', border: '3px solid rgba(255,255,255,0.1)', borderTopColor: '#3b82f6', borderRadius: '50%', animation: 'spin 0.8s linear infinite', margin: '0 auto 1rem' }}></div>
          <p>Loading NxtMock...</p>
        </div>
      </div>
    );
  }

  // 2. Mandatory Auth Gate: Unauthenticated users see AuthScreen
  if (!isAuthenticated) {
    return <AuthScreen />;
  }

  // 3. Authenticated: Candidate Home Dashboard
  if (viewMode === 'dashboard') {
    return (
      <>
        <HomeDashboard
          onStartInterview={() => setIsSetupOpen(true)}
          onSelectReport={handleSelectPastReport}
        />

        <SetupModal
          isOpen={isSetupOpen}
          onStart={startInterviewSession}
          onClose={() => setIsSetupOpen(false)}
        />
      </>
    );
  }

  // 4. Authenticated: Evaluation Report View
  if (viewMode === 'report' || isInterviewEnded) {
    return (
      <div className={styles.appContainer} style={{ minHeight: '100vh', height: 'auto', overflowY: 'auto' }}>
        <ReportDashboard
          reportData={reportData}
          evaluationText={evaluationReport}
          durationSeconds={durationSeconds}
          candidateName={candidateName}
          trackName={trackName}
          q1Title={isCvGrill ? 'Project Architecture' : (activeProblemId === 'two_sum' ? 'Two Sum' : 'Problem 1')}
          q2Title={isCvGrill ? 'Scaling & Trade-offs' : (activeProblemId === 'group_anagrams' ? 'Group Anagrams' : 'Problem 2')}
          isProcessing={isProcessing}
          onRestart={handleRestart}
          onBackToDashboard={() => {
            setViewMode('dashboard');
            setIsInterviewEnded(false);
          }}
        />
      </div>
    );
  }

  // 5. Authenticated: Live AI Interview Room
  return (
    <div className={styles.appContainer}>
      <header className={styles.header}>
        <div className={styles.logo}>
          <button
            className={styles.exitDashboardBtn}
            onClick={handleExitToDashboard}
            title="Exit to Dashboard"
          >
            <ArrowLeft size={14} /> Exit
          </button>
        </div>

        {/* Phase Progress Indicator */}
        <div className={styles.stageTracker}>
          {activeStages.map((stage, idx) => {
            const isCompleted = idx < currentStageIdx;
            const isCurrent = idx === currentStageIdx;
            return (
              <div
                key={stage.id}
                className={`${styles.stageBadge} ${isCurrent ? styles.stageActive : ''} ${isCompleted ? styles.stageCompleted : ''}`}
              >
                {isCompleted ? <CheckCircle size={13} /> : <Circle size={13} />}
                <span>{stage.label}</span>
              </div>
            );
          })}
        </div>

        <div className={styles.headerInfo}>
          <div className={styles.timer}>
            <span>⏱</span> {formatTime(timeLeft)}
          </div>
          {isRecording && (
            <div className={styles.recordingStatus}>
              <div className={styles.recDot}></div> REC
            </div>
          )}
          <div
            className={`${styles.networkStatus} ${networkSpeed.status === 'poor' ? styles.networkPoor : networkSpeed.status === 'fair' ? styles.networkFair : styles.networkGood}`}
            title={networkSpeed.rtt ? `Network Latency: ${networkSpeed.rtt}ms` : 'Connection Active'}
          >
            <span className={styles.networkDot}></span>
            <span>📶 {networkSpeed.label}</span>
          </div>
        </div>
      </header>

      <main className={styles.mainContent}>
        {/* Flexible Workspace (Question Tab + Resizer + Editor Tab) */}
        <div className={styles.workspaceContainer} ref={workspaceRef}>
          {/* Question Tab */}
          <section
            className={`${styles.problemPanel} ${isQuestionCollapsed ? styles.problemPanelCollapsed : ''} ${isQuestionExpanded ? styles.problemPanelExpanded : ''}`}
            style={
              isQuestionCollapsed
                ? { width: '48px', minWidth: '48px', maxWidth: '48px', flex: '0 0 48px' }
                : isQuestionExpanded
                ? { width: '100%', minWidth: '100%', flex: '1 1 100%' }
                : { width: `${questionWidth}%`, flex: `0 0 ${questionWidth}%` }
            }
          >
            {isQuestionCollapsed ? (
              <div
                className={styles.collapsedSidebar}
                onClick={() => { setIsQuestionCollapsed(false); setIsQuestionExpanded(false); }}
                title="Click to expand Question tab"
              >
                <button
                  className={styles.expandSidebarBtn}
                  onClick={(e) => { e.stopPropagation(); setIsQuestionCollapsed(false); setIsQuestionExpanded(false); }}
                  title="Expand Question Panel"
                >
                  <PanelLeftOpen size={16} />
                </button>
                <span className={styles.collapsedSidebarText}>
                  {isCvGrill ? 'CV & Projects' : 'Problem Statement'}
                </span>
              </div>
            ) : (
              <>
                {/* Header with Title and Expand / Collapse Controls */}
                <div className={styles.panelHeaderBar}>
                  <div className={styles.panelHeaderTitle}>
                    <FileText size={14} />
                    <span>{isCvGrill ? 'CV & Project Deep-Dive' : 'Problem Statement'}</span>
                  </div>

                  <div className={styles.panelHeaderControls}>
                    <button
                      className={styles.panelControlBtn}
                      onClick={toggleQuestionExpanded}
                      title={isQuestionExpanded ? "Restore Split View" : "Maximize Question"}
                    >
                      {isQuestionExpanded ? <Minimize2 size={13} /> : <Maximize2 size={13} />}
                      <span>{isQuestionExpanded ? 'Split' : 'Maximize'}</span>
                    </button>

                    <button
                      className={styles.panelControlBtn}
                      onClick={toggleQuestionCollapsed}
                      title="Collapse Question Tab"
                    >
                      <PanelLeftClose size={13} />
                      <span>Collapse</span>
                    </button>
                  </div>
                </div>

                <div className={styles.problemScrollContent}>
                  {isCvGrill ? (
                    <div className={styles.cvProjectViewer}>
                      <div className={styles.cvViewerHeader}>
                        <span className={styles.cvModeBadge}>
                          <Sparkles size={14} /> CV & Project Deep-Dive
                        </span>
                        <h2>Candidate Profile & Projects</h2>
                        <p>{parsedCv?.summary || 'Technical profile summary extracted from your CV.'}</p>
                      </div>

                      {parsedCv?.skills?.length > 0 && (
                        <div className={styles.cvSkillsBox}>
                          <label>Identified Tech Stack & Skills</label>
                          <div className={styles.cvSkillsPills}>
                            {parsedCv.skills.map((s, i) => (
                              <span key={i} className={styles.cvSkillPill}>{s}</span>
                            ))}
                          </div>
                        </div>
                      )}

                      <div className={styles.cvProjectsList}>
                        <label style={{ fontSize: '0.82rem', fontWeight: 600, color: '#cbd5e1', marginBottom: '0.2rem', display: 'block' }}>
                          Flagship Projects Under Probing
                        </label>
                        {(parsedCv?.projects || [
                          { name: 'Primary Software Architecture', tech_stack: ['Python', 'FastAPI', 'Microservices'], summary: 'System architecture and core services under technical review.' }
                        ]).map((proj, idx) => (
                          <div key={idx} className={styles.cvProjectCard}>
                            <div className={styles.cvProjectCardHeader}>
                              <h4>{proj.name}</h4>
                              <span className={styles.cvProjectIdxBadge}>Project {idx + 1}</span>
                            </div>
                            <p className={styles.cvProjectSummary}>{proj.summary}</p>
                            {proj.architecture_highlights && (
                              <div className={styles.cvArchHighlight}>
                                <strong>Architecture:</strong> {proj.architecture_highlights}
                              </div>
                            )}
                            {proj.tech_stack?.length > 0 && (
                              <div className={styles.cvProjectTech}>
                                {proj.tech_stack.map((t, ti) => (
                                  <span key={ti} className={styles.cvTechTag}>{t}</span>
                                ))}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : problemHtml ? (
                    <div dangerouslySetInnerHTML={{ __html: problemHtml }} />
                  ) : (
                    <div className={styles.introEmptyState}>
                      <div className={styles.introBadge}>
                        <Sparkles size={16} /> Phase 1: Candidate Introduction
                      </div>
                      <h2>Welcome to Your Mock Interview, {candidateName}!</h2>
                      <p>Introduce yourself to {interviewerName}. Tell her about your experience, preferred tech stack, or recent projects.</p>

                      <button
                        className={styles.advanceBtn}
                        onClick={handleQuickAdvance}
                        disabled={isProcessing}
                      >
                        Ready for Question 1 &rarr;
                      </button>
                    </div>
                  )}
                </div>
              </>
            )}
          </section>

          {/* Draggable Resizer Splitter Divider */}
          {!isQuestionCollapsed && !isQuestionExpanded && (
            <div
              className={`${styles.resizerDivider} ${isDragging ? styles.resizerDragging : ''}`}
              onMouseDown={handleMouseDown}
              onDoubleClick={() => setQuestionWidth(40)}
              title="Drag to adjust Question vs Code Editor width (Double-click to reset 40/60)"
            >
              <div className={styles.resizerGrip} />
            </div>
          )}

          {/* Code Editor Tab */}
          {!isQuestionExpanded && (
            <section
              className={`${styles.editorPanel} ${isQuestionCollapsed ? styles.editorPanelFull : ''}`}
              style={{
                flex: isQuestionCollapsed ? '1 1 auto' : `1 1 calc(${100 - questionWidth}% - 8px)`
              }}
            >
              <div className={styles.editorHeader}>
                <div className={styles.editorHeaderLeft}>
                  {isQuestionCollapsed && (
                    <button
                      className={styles.restoreQuestionBtn}
                      onClick={() => setIsQuestionCollapsed(false)}
                      title="Show Question Tab"
                    >
                      <PanelLeftOpen size={14} />
                      <span>Show Problem</span>
                    </button>
                  )}

                  <select
                    className={styles.languageSelect}
                    value={language}
                    onChange={handleLanguageChange}
                  >
                    <option value="python">Python 3</option>
                    <option value="cpp">C++17 (gcc)</option>
                    <option value="javascript">JavaScript (Node.js)</option>
                    <option value="java">Java 17</option>
                  </select>

                  <div className={styles.editorPhaseTag}>
                    Phase: <strong>{currentPhase}</strong>
                  </div>
                </div>

                <div className={styles.editorHeaderActions}>
                  <button
                    className={styles.panelControlBtn}
                    onClick={toggleEditorExpanded}
                    title={isQuestionCollapsed ? "Restore Split View" : "Maximize Code Editor (Hide Question)"}
                  >
                    {isQuestionCollapsed ? <Columns size={13} /> : <Maximize2 size={13} />}
                    <span>{isQuestionCollapsed ? 'Split View' : 'Expand Editor'}</span>
                  </button>

                  <button
                    className={styles.headerRunBtn}
                    onClick={handleRunCode}
                    disabled={!isEditorEnabled || isRunningCode || isSubmittingCode}
                    title={isCvGrill ? "Test notes syntax" : "Run code against sample test cases"}
                  >
                    <Play size={13} />
                    {isRunningCode ? 'Running...' : (isCvGrill ? 'Check Notes' : 'Run')}
                  </button>

                  <button
                    className={styles.headerSubmitBtn}
                    onClick={handleSubmitSolution}
                    disabled={!isEditorEnabled || isRunningCode || isSubmittingCode}
                    title={isCvGrill ? "Submit notes to interviewer" : "Submit solution"}
                  >
                    <Send size={13} />
                    {isSubmittingCode ? 'Submitting...' : (isCvGrill ? 'Submit Notes' : 'Submit')}
                  </button>
                </div>
              </div>

              <div className={styles.editorContainer}>
                <Editor
                  height="100%"
                  language={language === 'cpp' ? 'cpp' : language === 'javascript' ? 'javascript' : language === 'java' ? 'java' : 'python'}
                  theme="vs-dark"
                  value={code}
                  onChange={(value) => {
                    const val = value || '';
                    setCode(val);
                    codePerLangRef.current[language] = val;
                  }}
                  options={{
                    minimap: { enabled: false },
                    fontSize: 14,
                    readOnly: !isEditorEnabled
                  }}
                />

                {!isEditorEnabled && (
                  <div className={styles.editorOverlay}>
                    <Lock size={32} style={{ marginBottom: '1rem', color: '#60a5fa' }} />
                    <p>The code editor unlocks in <strong>Question 1</strong> & <strong>Question 2</strong>.<br />Follow {interviewerName}'s guidance or click "Ready for Question 1".</p>
                    {currentPhase === 'Intro' && (
                      <button
                        className={styles.advanceBtn}
                        onClick={handleQuickAdvance}
                        disabled={isProcessing}
                        style={{ marginTop: '1rem' }}
                      >
                        Start Question 1 Now &rarr;
                      </button>
                    )}
                  </div>
                )}
              </div>

              {/* Test Case Execution Sandbox Console */}
              <TestConsole
                onRunCode={handleRunCode}
                onSubmitSolution={handleSubmitSolution}
                isRunning={isRunningCode}
                isSubmitting={isSubmittingCode}
                testResults={testResults}
                isEditorEnabled={isEditorEnabled}
              />
            </section>
          )}
        </div>

        {/* Fixed Interviewer & Candidate Video Panel */}
        <section className={styles.videoPanel}>
          <div className={`${styles.videoBox} ${isAiSpeaking ? styles.aiSpeakingBox : ''}`}>
            <div className={`${styles.aiAvatarWrapper} ${isAiSpeaking ? styles.aiAvatarSpeaking : ''}`}>
              <img
                src="/julie_avatar.jpg"
                alt="Senior Interviewer {interviewerName}"
                className={styles.aiAvatarImg}
              />
            </div>
            <div className={styles.videoLabel}>
              {interviewerName} {isAiSpeaking ? '🔊 Speaking...' : isProcessing ? '⏳ Thinking...' : ''}
            </div>
          </div>

          <div className={styles.videoBox}>
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className={styles.videoElement}
              style={{ display: isVideoOn ? 'block' : 'none' }}
            />
            {!isVideoOn && <div className={styles.cameraOffPlaceholder}>Camera Off</div>}
            <div className={styles.videoLabel}>You {isRecording ? '🎙 Speaking' : ''}</div>
          </div>

          {/* Subtitles Box in Video Panel */}
          {subtitles && (
            <div className={styles.subtitlesBox}>
              {subtitles}
            </div>
          )}
        </section>
      </main>

      {/* Dedicated Bottom Footer Bar */}
      <footer className={styles.bottomFooter}>
        <div className={styles.controlBar}>
          <button
            className={styles.controlBtn}
            onClick={() => setIsVideoOn(!isVideoOn)}
            title={isVideoOn ? "Turn off camera" : "Turn on camera"}
          >
            {isVideoOn ? <Video size={18} /> : <VideoOff size={18} />}
          </button>

          <button
            className={styles.controlBtn}
            onClick={() => {
              if (isEditorEnabled && !isProcessing) {
                handleUserAudioSubmission("Could you please review my current code and provide feedback or hints?");
              }
            }}
            disabled={!isEditorEnabled || isProcessing}
            title="Ask Interviewer to Review Code"
          >
            <Code size={18} />
          </button>

          {/* Push-to-Talk Mic Button */}
          <button
            className={`${styles.controlBtn} ${styles.primary} ${isRecording ? styles.recording : ''}`}
            onClick={handlePushToTalk}
            disabled={isProcessing}
            title={isRecording ? "Tap to submit answer" : "Tap to Speak"}
          >
            {isRecording ? <MicOff size={20} /> : <Mic size={20} />}
          </button>

          {/* Quick text input fallback */}
          <form onSubmit={handleTextSubmit} className={styles.textForm}>
            <input
              type="text"
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              placeholder="Type your response to {interviewerName}..."
              className={styles.textInput}
              disabled={isProcessing}
            />
            <button
              type="submit"
              className={styles.sendBtn}
              disabled={!textInput.trim() || isProcessing}
              title="Send response"
            >
              <Send size={14} />
            </button>
          </form>

          <button className={`${styles.controlBtn} ${styles.danger}`} title="End interview" onClick={handleEndInterview}>
            <Phone size={18} style={{ transform: 'rotate(135deg)' }} />
          </button>
        </div>
      </footer>
    </div>
  );
}

export default App;
