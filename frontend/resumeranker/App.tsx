
import * as React from 'react';
import { useState, useRef, useEffect } from 'react';
import Header from './components/Header';
import Footer from './components/Footer';
import ResultsSection from './components/ResultsSection';
import PricingSection from './components/PricingSection';
import { Candidate, RankedCandidate, AppState, DetailedAnalysis } from './types';
import { uploadResumes, getScores, generateReport, getTotalResumes } from './services/api';

const App: React.FC = () => {
  const [appState, setAppState] = useState<AppState>(AppState.IDLE);
  const [resumes, setResumes] = useState<Candidate[]>([]);
  const [totalResumesCount, setTotalResumesCount] = useState<number>(0);

  // JD State
  const [jdInputType, setJdInputType] = useState<'text' | 'file'>('text');
  const [jobDescription, setJobDescription] = useState<string>('');
  const [jdFile, setJdFile] = useState<File | null>(null);

  const [rankedCandidates, setRankedCandidates] = useState<RankedCandidate[]>([]);
  const [reportContent, setReportContent] = useState<string>('');
  const [errorMsg, setErrorMsg] = useState<string>('');
  
  // Loading State
  const [loadingMessageIndex, setLoadingMessageIndex] = useState(0);

  const resumeInputRef = useRef<HTMLInputElement>(null);
  const jdInputRef = useRef<HTMLTextAreaElement>(null);
  const jdFileInputRef = useRef<HTMLInputElement>(null);

  const loadingMessages = [
    "Reading and parsing resume documents...",
    "Extracting key skills and experience...",
    "Comparing candidates against job requirements...",
    "Evaluating cultural fit and qualifications...",
    "Generating comprehensive ranking report..."
  ];

  useEffect(() => {
    let interval: any;
    if (appState === AppState.ANALYZING) {
      setLoadingMessageIndex(0);
      interval = setInterval(() => {
        setLoadingMessageIndex((prev) => (prev + 1) % loadingMessages.length);
      }, 2500); // Change message every 2.5s
    }
    return () => clearInterval(interval);
  }, [appState]);

  const handleResumeUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files.length > 0) {
      const files: File[] = Array.from(event.target.files);

      // 1. Optimistically add files with 'uploading' status
      const newCandidates: Candidate[] = files.map(file => ({
        id: Math.random().toString(36).substr(2, 9),
        name: file.name,
        content: "Pending upload...",
        status: 'uploading'
      }));
      
      setResumes(prev => [...prev, ...newCandidates]);

      try {
        // 2. Upload to backend
        await uploadResumes(files);

        // 3. Update status to success
        setResumes(prev => prev.map(candidate => {
          const matchingNew = newCandidates.find(nc => nc.id === candidate.id);
          if (matchingNew) {
            return { ...candidate, status: 'success', content: "Uploaded to backend" };
          }
          return candidate;
        }));

        setTotalResumesCount(prev => prev + files.length);

        if (appState === AppState.IDLE) {
          setAppState(AppState.RESUMES_UPLOADED);
        }
      } catch (e: any) {
        console.error("Failed to upload resumes", e);
        setErrorMsg("Failed to upload resumes: " + e.message);
        
        // 4. Update status to error
        setResumes(prev => prev.map(candidate => {
          const matchingNew = newCandidates.find(nc => nc.id === candidate.id);
          if (matchingNew) {
            return { ...candidate, status: 'error' };
          }
          return candidate;
        }));
      }
      
      // Reset input so the same file can be selected again if needed (though unlikely immediately)
      if (resumeInputRef.current) {
        resumeInputRef.current.value = '';
      }
    }
  };

  const handleUseExistingResumes = async () => {
    try {
      const total = await getTotalResumes();
      if (total > 0) {
        // Populate resumes with a placeholder to enable the next step
        setResumes([{ id: 'existing', name: `${total} Existing Resumes`, content: 'Existing database content', status: 'success' }]);
        setTotalResumesCount(total);
        setAppState(AppState.RESUMES_UPLOADED);
      } else {
        alert("No existing resumes found in the database. Please upload new ones.");
      }
    } catch (error) {
      console.error("Failed to check existing resumes", error);
      alert("Failed to check existing resumes.");
    }
  };

  const handleJdFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files.length > 0) {
      setJdFile(event.target.files[0]);
      setAppState(AppState.READY_TO_RANK);
    }
  };

  const handleRank = async () => {
    if (resumes.length === 0) {
      setErrorMsg("Please upload resumes first.");
      return;
    }

    // Validation based on input type
    if (jdInputType === 'text' && !jobDescription) return;
    if (jdInputType === 'file' && !jdFile) return;

    setAppState(AppState.ANALYZING);
    setErrorMsg('');

    try {
      // 1. Get Scores (Initial lightweight check, can still be useful or we can rely solely on report)
      // We still call it to ensure backend is processing, but we might rely on generateReport for final data
      // const scoresData = await getScores(jdFile, jdInputType === 'text' ? jobDescription : null);

      // 2. Generate Report (This now contains the detailed JSON)
      const reportData = await generateReport(jdFile, jdInputType === 'text' ? jobDescription : null);
      
      let candidates: RankedCandidate[] = [];

      if (reportData.detailed_analysis) {
        candidates = reportData.detailed_analysis.map((analysis: DetailedAnalysis, index: number) => {
           const breakdown = analysis.scoring_breakdown;
           
           // Collect pros from various positive signals
           const pros: string[] = [];
           if (breakdown.skills_competency?.key_evidence) pros.push(...breakdown.skills_competency.key_evidence);
           if (breakdown.experience_depth?.quantifiable_wins) pros.push(...breakdown.experience_depth.quantifiable_wins);
           
           // Collect cons from various negative signals
           const cons: string[] = [];
           if (breakdown.skills_competency?.missing_critical_skills) cons.push(...breakdown.skills_competency.missing_critical_skills);
           if (breakdown.role_trajectory?.red_flags) cons.push(...breakdown.role_trajectory.red_flags);
           if (breakdown.education_requirements?.red_flags) cons.push(...breakdown.education_requirements.red_flags);
           if (breakdown.strategic_fit?.red_flags) cons.push(...breakdown.strategic_fit.red_flags);

           // Normalize scores to 0-100 based on max_score
           const normalizeScore = (section: any) => {
             if (!section || !section.max_score) return 0;
             return Math.round((section.score / section.max_score) * 100);
           };

           return {
             id: `candidate-${index}`,
             name: analysis.candidateName,
             score: analysis.overallScore,
             experienceScore: normalizeScore(breakdown.experience_depth),
             skillsScore: normalizeScore(breakdown.skills_competency),
             summary: analysis.final_verdict.main_argument,
             pros: pros,
             cons: cons,
             detailedAnalysis: analysis
           };
        }).sort((a, b) => b.score - a.score);
      } else {
        // Fallback if detailed_analysis is missing, maybe parse from summary or use getScores if needed
        console.warn("Detailed analysis missing from report, falling back to legacy display if applicable.");
      }

      setRankedCandidates(candidates);
      setReportContent(reportData.summary_report || reportData.results || "");

      setAppState(AppState.RESULTS);
    } catch (err: any) {
      console.error(err);
      setErrorMsg(err.message || "An unexpected error occurred during analysis.");
      setAppState(AppState.ERROR);
    }
  };

  const resetApp = () => {
    setResumes([]);
    setJobDescription('');
    setJdFile(null);
    setRankedCandidates([]);
    setReportContent('');
    setAppState(AppState.IDLE);
    setJdInputType('text');
    if (jdInputRef.current) jdInputRef.current.value = '';
    if (resumeInputRef.current) resumeInputRef.current.value = '';
    if (jdFileInputRef.current) jdFileInputRef.current.value = '';
  };

  // --- Render Helpers ---

  const renderHero = () => (
    <section className="py-16 sm:py-20 animate-fade-in">
      <div className="@container">
        <div className="flex flex-col gap-10 px-4">
          <div className="flex flex-col gap-4 text-center items-center">
            <h1 className="text-gray-900 dark:text-white text-4xl font-black leading-tight tracking-[-0.033em] @[480px]:text-5xl max-w-2xl">
              Hire Smarter, Not Harder. Find Your Perfect Candidate in Minutes.
            </h1>
            <h2 className="text-gray-600 dark:text-text-secondary-dark text-base font-normal leading-normal @[480px]:text-lg max-w-2xl">
              Start by providing resumes, then upload a job description to instantly rank candidates with the power of AI.
            </h2>
          </div>

          <div className="flex justify-center">
            <div className="w-full max-w-3xl flex flex-col items-center gap-8">

              {/* Step 1: Upload Resumes */}
              <div className="w-full flex flex-col items-center gap-6">
                <div className="w-full grid grid-cols-1 @[480px]:grid-cols-2 gap-6 items-stretch">
                  <button
                    onClick={() => resumeInputRef.current?.click()}
                    className="flex flex-col items-center justify-center gap-4 p-8 rounded-xl border-2 border-dashed border-gray-300 dark:border-gray-600 hover:border-primary dark:hover:border-primary hover:bg-blue-50 dark:hover:bg-primary/10 transition-all group"
                  >
                    <input
                      type="file"
                      multiple
                      ref={resumeInputRef}
                      className="hidden"
                      accept=".pdf,.docx,.doc"
                      onChange={handleResumeUpload}
                    />
                    <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center group-hover:scale-110 transition-transform">
                      <span className="material-symbols-outlined text-primary text-3xl">upload_file</span>
                    </div>
                    <div className="text-center">
                      <p className="text-lg font-bold text-gray-900 dark:text-white">
                        {resumes.length > 0 ? "Add More Resumes" : "Upload Resumes"}
                      </p>
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        Drag & drop or click to select files (PDF, DOCX)
                      </p>
                    </div>
                  </button>

                  <button
                    onClick={handleUseExistingResumes}
                    className="flex flex-col items-center justify-center gap-4 p-8 rounded-xl border border-gray-200 dark:border-border-dark bg-white dark:bg-surface-dark hover:border-primary dark:hover:border-primary hover:bg-blue-50 dark:hover:bg-primary/10 transition-all group cursor-pointer"
                  >
                    <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center group-hover:scale-110 transition-transform">
                      <span className="material-symbols-outlined text-primary text-3xl">storage</span>
                    </div>
                    <div className="text-center">
                      <p className="text-lg font-bold text-gray-900 dark:text-white">Use Existing Database</p>
                      <p className="text-sm text-gray-500 dark:text-gray-400">Skip upload</p>
                    </div>
                  </button>
                </div>
                
                {/* Uploaded Files List */}
                {resumes.length > 0 && (
                  <div className="w-full max-w-2xl bg-white dark:bg-surface-dark rounded-xl border border-gray-200 dark:border-border-dark overflow-hidden shadow-sm animate-fade-in">
                    <div className="px-4 py-3 border-b border-gray-200 dark:border-border-dark bg-gray-50 dark:bg-white/5 flex justify-between items-center">
                      <h3 className="font-bold text-sm text-gray-700 dark:text-gray-200">Uploaded Files ({resumes.length})</h3>
                    </div>
                    <ul className="divide-y divide-gray-100 dark:divide-gray-800 max-h-60 overflow-y-auto">
                      {resumes.map((resume) => (
                        <li key={resume.id} className="px-4 py-3 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-white/5 transition-colors">
                          <div className="flex items-center gap-3 overflow-hidden">
                             <div className="p-2 rounded-lg bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 shrink-0">
                               <span className="material-symbols-outlined text-xl">description</span>
                             </div>
                             <span className="text-sm font-medium text-gray-700 dark:text-gray-200 truncate">{resume.name}</span>
                          </div>
                          <div className="flex items-center gap-2 shrink-0">
                            {resume.status === 'uploading' && (
                               <div className="flex items-center gap-2 text-blue-500">
                                  <span className="text-xs font-medium hidden sm:inline">Uploading...</span>
                                  <span className="material-symbols-outlined animate-spin text-xl">progress_activity</span>
                               </div>
                            )}
                            {resume.status === 'success' && (
                               <span className="material-symbols-outlined text-green-500 text-xl" title="Uploaded">check_circle</span>
                            )}
                            {resume.status === 'error' && (
                               <div className="flex items-center gap-1 text-red-500" title="Upload Failed">
                                 <span className="material-symbols-outlined text-xl">error</span>
                               </div>
                            )}
                          </div>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              {/* Step 2: Job Description */}
              <div className={`w-full flex flex-col items-center gap-4 transition-all duration-500 ${resumes.length > 0 ? 'opacity-100 translate-y-0' : 'opacity-50 translate-y-4 pointer-events-none'}`}>
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-gray-500 dark:text-gray-400">arrow_downward</span>
                  <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Next Step: Add Job Description</p>
                </div>

                <div className="w-full max-w-xl bg-gray-100 dark:bg-surface-dark rounded-lg p-4 transition-all border border-transparent focus-within:border-primary focus-within:ring-1 focus-within:ring-primary">

                  {/* Input Type Toggle */}
                  <div className="flex p-1 bg-gray-200 dark:bg-background-dark rounded-lg mb-4">
                    <button
                      onClick={() => setJdInputType('text')}
                      className={`flex-1 flex items-center justify-center gap-2 py-2 text-sm font-bold rounded-md transition-all ${jdInputType === 'text' ? 'bg-white dark:bg-surface-dark shadow-sm text-primary' : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'}`}
                    >
                      <span className="material-symbols-outlined text-base">edit_note</span>
                      Paste Text
                    </button>
                    <button
                      onClick={() => setJdInputType('file')}
                      className={`flex-1 flex items-center justify-center gap-2 py-2 text-sm font-bold rounded-md transition-all ${jdInputType === 'file' ? 'bg-white dark:bg-surface-dark shadow-sm text-primary' : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'}`}
                    >
                      <span className="material-symbols-outlined text-base">attach_file</span>
                      Upload File
                    </button>
                  </div>

                  {/* Text Input */}
                  {jdInputType === 'text' && (
                    <textarea
                      ref={jdInputRef}
                      className="w-full bg-transparent border-none text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:ring-0 resize-none h-24 p-2 text-sm"
                      placeholder="Paste your Job Description here..."
                      onChange={(e) => {
                        if (e.target.value.length > 10) {
                          setJobDescription(e.target.value);
                          setAppState(AppState.READY_TO_RANK);
                        } else {
                          setJobDescription('');
                          setAppState(AppState.RESUMES_UPLOADED);
                        }
                      }}
                    />
                  )}

                  {/* File Input */}
                  {jdInputType === 'file' && (
                    <div
                      onClick={() => jdFileInputRef.current?.click()}
                      className="border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg p-6 flex flex-col items-center justify-center cursor-pointer hover:bg-gray-50 dark:hover:bg-background-dark/50 transition-colors"
                    >
                      <input
                        type="file"
                        ref={jdFileInputRef}
                        className="hidden"
                        accept=".pdf,.docx,.txt"
                        onChange={handleJdFileChange}
                      />
                      {jdFile ? (
                        <div className="flex items-center gap-3 text-primary">
                          <span className="material-symbols-outlined text-3xl">description</span>
                          <div className="text-left">
                            <p className="font-bold text-sm line-clamp-1 break-all">{jdFile.name}</p>
                            <p className="text-xs text-gray-500">{(jdFile.size / 1024).toFixed(1)} KB</p>
                          </div>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setJdFile(null);
                              setAppState(AppState.RESUMES_UPLOADED);
                              if (jdFileInputRef.current) jdFileInputRef.current.value = '';
                            }}
                            className="ml-2 p-1 hover:bg-red-100 rounded-full text-red-500"
                          >
                            <span className="material-symbols-outlined text-lg">close</span>
                          </button>
                        </div>
                      ) : (
                        <>
                          <span className="material-symbols-outlined text-gray-400 text-3xl mb-2">cloud_upload</span>
                          <p className="text-sm font-medium text-gray-600 dark:text-gray-300">Click to upload JD</p>
                          <p className="text-xs text-gray-400 mt-1">PDF, DOCX, or TXT</p>
                        </>
                      )}
                    </div>
                  )}
                </div>

                {/* Step 3: Action */}
                <div className={`transition-all duration-300 ${(jdInputType === 'text' && jobDescription) || (jdInputType === 'file' && jdFile)
                  ? 'opacity-100 scale-100' : 'opacity-0 scale-95 pointer-events-none'
                  }`}>
                  <button
                    onClick={handleRank}
                    className="flex min-w-[200px] cursor-pointer items-center justify-center overflow-hidden rounded-lg h-12 px-6 bg-primary hover:bg-blue-600 text-white text-base font-bold leading-normal tracking-[0.015em] shadow-lg shadow-primary/25 transition-all active:scale-95"
                  >
                    <span className="truncate">Generate Ranking Report</span>
                    <span className="material-symbols-outlined ml-2">auto_awesome</span>
                  </button>
                </div>

              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );

  const renderFeatures = () => (
    <section id="about" className="py-16 sm:py-20 bg-gray-100 dark:bg-[#111a22] rounded-xl mx-4 sm:mx-8 lg:mx-20 mb-10">
      <div className="flex flex-col gap-10 px-4 py-10 @container">
        <div className="flex flex-col gap-4 text-center items-center">
          <h2 className="text-gray-900 dark:text-white tracking-light text-[32px] font-bold leading-tight @[480px]:text-4xl max-w-[720px]">
            Unlock a Faster, More Accurate Hiring Process
          </h2>
          <p className="text-gray-600 dark:text-text-secondary-dark text-base font-normal leading-normal max-w-[720px]">
            Our AI-driven platform analyzes resumes against your job description to identify the most qualified candidates, saving you time and effort.
          </p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 p-4 max-w-6xl mx-auto w-full">
          {[
            { icon: 'auto_awesome', title: 'AI-Powered Ranking', desc: 'Leverage advanced algorithms to score and rank candidates based on skills and experience.' },
            { icon: 'schedule', title: 'Save Time', desc: 'Drastically reduce manual screening time and focus on interviewing the best applicants.' },
            { icon: 'group', title: 'Find Top Talent', desc: 'Quickly identify high-potential candidates who are the best fit for the role.' }
          ].map((feature, idx) => (
            <div key={idx} className="flex gap-4 rounded-xl border border-gray-200 dark:border-border-dark bg-white dark:bg-surface-dark p-6 flex-col hover:border-primary/50 transition-colors">
              <div className="text-primary w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center">
                <span className="material-symbols-outlined">{feature.icon}</span>
              </div>
              <div className="flex flex-col gap-2">
                <h3 className="text-gray-900 dark:text-white text-lg font-bold leading-tight">{feature.title}</h3>
                <p className="text-gray-600 dark:text-text-secondary-dark text-sm leading-relaxed">{feature.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );

  const renderHowItWorks = () => (
    <section id="how-it-works" className="py-16 sm:py-20 border-t border-gray-200 dark:border-border-dark">
      <div className="flex flex-col items-center text-center">
        <h2 className="text-gray-900 dark:text-white text-[22px] font-bold leading-tight tracking-[-0.015em] px-4 pb-10">
          How It Works
        </h2>
        <div className="grid grid-cols-[40px_1fr] gap-x-4 px-4 w-full max-w-sm">
          {/* Step 1 */}
          <div className="flex flex-col items-center gap-1 pt-1">
            <div className="text-primary">
              <span className="material-symbols-outlined">upload_file</span>
            </div>
            <div className="w-[1.5px] bg-gray-200 dark:bg-border-dark h-full grow min-h-[40px]"></div>
          </div>
          <div className="flex flex-1 flex-col pb-8 text-left">
            <p className="text-gray-900 dark:text-white text-base font-medium leading-normal">1. Add Candidate Resumes</p>
            <p className="text-gray-600 dark:text-text-secondary-dark text-sm font-normal leading-normal">Upload multiple resumes or use your existing database.</p>
          </div>

          {/* Step 2 */}
          <div className="flex flex-col items-center gap-1">
            <div className="w-[1.5px] bg-gray-200 dark:bg-border-dark h-2"></div>
            <div className="text-primary">
              <span className="material-symbols-outlined">description</span>
            </div>
            <div className="w-[1.5px] bg-gray-200 dark:bg-border-dark h-full grow min-h-[40px]"></div>
          </div>
          <div className="flex flex-1 flex-col pb-8 text-left">
            <p className="text-gray-900 dark:text-white text-base font-medium leading-normal">2. Upload Job Description</p>
            <p className="text-gray-600 dark:text-text-secondary-dark text-sm font-normal leading-normal">Provide the role requirements and responsibilities.</p>
          </div>

          {/* Step 3 */}
          <div className="flex flex-col items-center gap-1 pb-1">
            <div className="w-[1.5px] bg-gray-200 dark:bg-border-dark h-2"></div>
            <div className="text-primary">
              <span className="material-symbols-outlined">leaderboard</span>
            </div>
          </div>
          <div className="flex flex-1 flex-col pt-1 text-left">
            <p className="text-gray-900 dark:text-white text-base font-medium leading-normal">3. Get Ranked Report</p>
            <p className="text-gray-600 dark:text-text-secondary-dark text-sm font-normal leading-normal">Receive an instant, data-driven report ranking all candidates.</p>
          </div>
        </div>
      </div>
    </section>
  );

  const renderLoading = () => (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-8 animate-fade-in">
      {/* Spinner */}
      <div className="relative w-24 h-24">
        <div className="absolute inset-0 rounded-full border-4 border-gray-200 dark:border-gray-700"></div>
        <div className="absolute inset-0 rounded-full border-4 border-primary border-t-transparent animate-spin"></div>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="material-symbols-outlined text-primary text-3xl animate-pulse">psychology</span>
        </div>
      </div>
      
      {/* Text and Progress */}
      <div className="text-center space-y-4 max-w-md w-full px-4">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
          Analyzing {totalResumesCount} Candidates
        </h2>
        
        <div className="space-y-2">
          <p className="text-gray-500 dark:text-text-secondary-dark min-h-[24px] transition-all duration-300 text-sm sm:text-base">
            {loadingMessages[loadingMessageIndex]}
          </p>
          
          {/* Progress Bar */}
          <div className="h-1.5 w-full bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
            <div 
              className="h-full bg-primary transition-all duration-500 ease-out"
              style={{ width: `${((loadingMessageIndex + 1) / loadingMessages.length) * 100}%` }}
            ></div>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="relative flex min-h-screen w-full flex-col overflow-x-hidden bg-background-light dark:bg-background-dark">
      <div className="layout-container flex h-full grow flex-col">
        <Header />

        <main className="flex-1 flex flex-col">
          {errorMsg && (
            <div className="bg-red-500/10 border border-red-500 text-red-500 p-4 mx-4 sm:mx-8 lg:mx-20 mt-6 rounded-lg flex items-center gap-3">
              <span className="material-symbols-outlined">error</span>
              <span>{errorMsg}</span>
              <button onClick={() => setAppState(AppState.READY_TO_RANK)} className="ml-auto hover:underline">Try Again</button>
            </div>
          )}

          {appState === AppState.RESULTS ? (
            <ResultsSection candidates={rankedCandidates} reportContent={reportContent} onReset={resetApp} />
          ) : appState === AppState.ANALYZING ? (
            renderLoading()
          ) : (
            <>
              {renderHero()}
              {renderFeatures()}
              {renderHowItWorks()}
              <PricingSection />
            </>
          )}
        </main>

        <Footer />
      </div>
    </div>
  );
};

export default App;
