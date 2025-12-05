
export interface Candidate {
  id: string;
  name: string;
  content: string; // The raw text content of the resume
  status?: 'uploading' | 'success' | 'error';
}

export interface ScoringSection {
  score: number;
  max_score: number;
  reasoning: string;
  key_evidence?: string[];
  missing_critical_skills?: string[];
  quantifiable_wins?: string[];
  red_flags?: string[];
}

export interface ScoringBreakdown {
  skills_competency?: ScoringSection;
  experience_depth?: ScoringSection;
  role_trajectory?: ScoringSection;
  education_requirements?: ScoringSection;
  strategic_fit?: ScoringSection;
}

export interface FinalVerdict {
  decision: string;
  main_argument: string;
  hiring_manager_notes: string;
}

export interface DetailedAnalysis {
  candidateName: string;
  overallScore: number;
  scoring_breakdown: ScoringBreakdown;
  final_verdict: FinalVerdict;
}

export interface RankedCandidate {
  id?: string;
  name: string;
  score: number;
  experienceScore?: number;
  skillsScore?: number;
  summary: string;
  pros: string[];
  cons: string[];
  fileName?: string;
  detailedAnalysis?: DetailedAnalysis; // Optional full analysis object
}

export interface RankingResult {
  candidates: RankedCandidate[];
}

export enum AppState {
  IDLE = 'IDLE',
  RESUMES_UPLOADED = 'RESUMES_UPLOADED',
  READY_TO_RANK = 'READY_TO_RANK',
  ANALYZING = 'ANALYZING',
  RESULTS = 'RESULTS',
  ERROR = 'ERROR'
}
