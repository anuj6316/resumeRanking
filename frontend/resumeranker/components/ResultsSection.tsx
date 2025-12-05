
import * as React from 'react';
import { useState, useMemo, useRef } from 'react';
import { RankedCandidate } from '../types';
import ReactMarkdown, { Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { API_BASE_URL } from '../services/api';

interface ResultsSectionProps {
  candidates: RankedCandidate[];
  reportContent: string;
  onReset: () => void;
}

// Helper to determine status based on score
const getStatus = (score: number) => {
  if (score >= 80) return { label: 'Shortlisted', color: 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20' };
  if (score >= 60) return { label: 'In Review', color: 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20' };
  return { label: 'Rejected', color: 'bg-red-500/10 text-red-500 border-red-500/20' };
};

const MarkdownComponents: Components = {
  h1: ({node, ...props}) => <h1 className="text-2xl font-bold mt-8 mb-4 text-gray-900 dark:text-white border-b pb-2 border-gray-200 dark:border-gray-700" {...props} />,
  h2: ({node, ...props}) => <h2 className="text-xl font-semibold mt-8 mb-4 text-gray-900 dark:text-white flex items-center gap-2" {...props} />,
  h3: ({node, ...props}) => <h3 className="text-lg font-semibold mt-6 mb-3 text-gray-800 dark:text-gray-200" {...props} />,
  p: ({node, ...props}) => <p className="mb-4 leading-7 text-gray-600 dark:text-gray-300" {...props} />,
  ul: ({node, ...props}) => <ul className="list-disc pl-6 mb-4 space-y-2 text-gray-600 dark:text-gray-300" {...props} />,
  ol: ({node, ...props}) => <ol className="list-decimal pl-6 mb-4 space-y-2 text-gray-600 dark:text-gray-300" {...props} />,
  li: ({node, ...props}) => <li className="pl-1" {...props} />,
  table: ({node, ...props}) => (
    <div className="overflow-x-auto my-6 rounded-lg border border-gray-200 dark:border-[#324d67] shadow-sm">
      <table className="w-full text-left border-collapse" {...props} />
    </div>
  ),
  thead: ({node, ...props}) => <thead className="bg-gray-50 dark:bg-[#233648]" {...props} />,
  tbody: ({node, ...props}) => <tbody className="divide-y divide-gray-200 dark:divide-[#324d67] bg-white dark:bg-[#192633]" {...props} />,
  tr: ({node, ...props}) => <tr className="hover:bg-gray-50 dark:hover:bg-[#1c2a3a] transition-colors" {...props} />,
  th: ({node, ...props}) => <th className="px-6 py-4 text-xs font-semibold text-gray-500 dark:text-gray-300 uppercase tracking-wider" {...props} />,
  td: ({node, ...props}) => <td className="px-6 py-4 text-sm text-gray-700 dark:text-gray-300 whitespace-normal leading-relaxed" {...props} />,
  blockquote: ({node, ...props}) => (
    <blockquote className="border-l-4 border-primary/50 pl-4 py-1 my-6 italic text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-primary/5 rounded-r-lg" {...props} />
  ),
  code: ({node, ...props}) => <code className="bg-gray-100 dark:bg-[#233648] rounded px-1.5 py-0.5 text-sm font-mono text-pink-600 dark:text-pink-400" {...props} />,
  a: ({node, ...props}) => <a className="text-primary hover:text-blue-600 dark:hover:text-blue-400 hover:underline cursor-pointer transition-colors" {...props} />,
  hr: ({node, ...props}) => <hr className="my-8 border-gray-200 dark:border-[#324d67]" {...props} />,
};

const ResultsSection: React.FC<ResultsSectionProps> = ({ candidates, reportContent, onReset }) => {
  const [activeTab, setActiveTab] = useState<'All' | 'Shortlisted' | 'Rejected'>('All');
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedRow, setExpandedRow] = useState<string | null>(null);
  const rowRefs = useRef<{ [key: string]: HTMLTableRowElement | null }>({});

  // Calculate Stats
  const stats = useMemo(() => {
    const scores = candidates.map(c => c.score);
    const maxScore = Math.max(...scores, 0);
    const avgScore = scores.length ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : 0;
    const shortlisted = candidates.filter(c => c.score >= 80).length;
    const rejected = candidates.filter(c => c.score < 60).length;
    
    return { maxScore, avgScore, shortlisted, rejected, total: candidates.length };
  }, [candidates]);

  // Filter Candidates
  const filteredCandidates = useMemo(() => {
    return candidates.filter(c => {
      const matchesSearch = c.name.toLowerCase().includes(searchQuery.toLowerCase()) || 
                            c.pros.some(p => p.toLowerCase().includes(searchQuery.toLowerCase()));
      
      if (activeTab === 'All') return matchesSearch;
      if (activeTab === 'Shortlisted') return matchesSearch && c.score >= 80;
      if (activeTab === 'Rejected') return matchesSearch && c.score < 60; // Assuming < 60 is rejected for this filter logic
      return matchesSearch;
    });
  }, [candidates, activeTab, searchQuery]);

  const toggleRow = (id: string) => {
    const isOpening = expandedRow !== id;
    setExpandedRow(isOpening ? id : null);
    
    if (isOpening) {
        // Smooth scroll to the row after expansion
        setTimeout(() => {
            rowRefs.current[id]?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }, 50);
    }
  };

  return (
    <div className="w-full max-w-[1400px] mx-auto p-4 sm:p-6 animate-fade-in font-display">
      {/* Header Area */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Ranking Report</h1>
          </div>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {stats.total} candidates evaluated • Last updated {new Date().toLocaleDateString()}
          </p>
        </div>
        <div className="flex gap-3">
           <button 
            onClick={onReset}
            className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-[#192633] border border-gray-200 dark:border-[#233648] rounded-lg hover:bg-gray-50 dark:hover:bg-[#233648] transition-colors"
           >
             Start Over
           </button>
           <button 
            onClick={() => window.print()}
            className="px-4 py-2 text-sm font-medium text-white bg-primary rounded-lg hover:bg-blue-600 transition-colors shadow-lg shadow-primary/25"
           >
             Download PDF
           </button>
        </div>
      </div>

      {/* Detailed Analysis - Prioritized at Top */}
      <div className="mb-10">
        <details className="group">
          <summary className="flex items-center gap-2 text-lg font-bold text-gray-900 dark:text-white cursor-pointer list-none mb-4 select-none">
            <span className="material-symbols-outlined text-[24px] transition-transform group-open:rotate-90">chevron_right</span>
            Executive Summary
          </summary>
          <div className="p-8 bg-white dark:bg-[#192633] border border-gray-200 dark:border-[#233648] rounded-xl shadow-sm">
             <div className="max-w-none">
               <ReactMarkdown 
                 remarkPlugins={[remarkGfm]} 
                 components={MarkdownComponents}
               >
                 {reportContent}
               </ReactMarkdown>
             </div>
          </div>
        </details>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <div className="p-5 rounded-xl bg-[#111922] border border-[#233648] relative overflow-hidden group">
          <div className="relative z-10">
            <p className="text-xs font-medium text-gray-400 mb-1">Top Score</p>
            <div className="flex items-baseline gap-2">
              <h3 className="text-3xl font-bold text-white">{stats.maxScore}</h3>
              <span className="text-sm text-gray-500">/ 100</span>
            </div>
          </div>
          <div className="absolute bottom-0 left-0 w-full h-1 bg-gray-800">
             <div className="h-full bg-emerald-500 transition-all duration-1000" style={{ width: `${stats.maxScore}%` }}></div>
          </div>
        </div>
        
        <div className="p-5 rounded-xl bg-[#111922] border border-[#233648] relative overflow-hidden">
          <div className="relative z-10">
            <p className="text-xs font-medium text-gray-400 mb-1">Average Score</p>
            <h3 className="text-3xl font-bold text-white">{stats.avgScore}</h3>
          </div>
          <div className="absolute bottom-0 left-0 w-full h-1 bg-gray-800">
             <div className="h-full bg-yellow-500 transition-all duration-1000" style={{ width: `${stats.avgScore}%` }}></div>
          </div>
        </div>

        <div className="p-5 rounded-xl bg-[#111922] border border-[#233648] relative overflow-hidden">
          <div className="relative z-10">
            <p className="text-xs font-medium text-gray-400 mb-1">Shortlisted</p>
            <h3 className="text-3xl font-bold text-emerald-400">{stats.shortlisted}</h3>
          </div>
          <div className="absolute bottom-0 left-0 w-full h-1 bg-gray-800">
             <div className="h-full bg-emerald-500 transition-all duration-1000" style={{ width: `${(stats.shortlisted / stats.total) * 100}%` }}></div>
          </div>
        </div>

        <div className="p-5 rounded-xl bg-[#111922] border border-[#233648] relative overflow-hidden">
          <div className="relative z-10">
            <p className="text-xs font-medium text-gray-400 mb-1">Rejected</p>
            <h3 className="text-3xl font-bold text-red-400">{stats.rejected}</h3>
          </div>
          <div className="absolute bottom-0 left-0 w-full h-1 bg-gray-800">
             <div className="h-full bg-red-500 transition-all duration-1000" style={{ width: `${(stats.rejected / stats.total) * 100}%` }}></div>
          </div>
        </div>
      </div>

      {/* Filters & Search */}
      <div className="flex flex-col sm:flex-row justify-between items-center gap-4 mb-6">
        <div className="flex p-1 bg-[#111922] border border-[#233648] rounded-lg">
          {(['All', 'Shortlisted', 'Rejected'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-1.5 text-sm font-medium rounded-md transition-all ${
                activeTab === tab 
                  ? 'bg-primary text-white shadow-sm' 
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        <div className="relative w-full sm:w-auto min-w-[300px]">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 material-symbols-outlined text-[20px]">search</span>
          <input 
            type="text" 
            placeholder="Search by name, skills..." 
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-[#111922] border border-[#233648] rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/50 transition-all"
          />
        </div>
      </div>

      {/* Candidates Table */}
      <div className="bg-[#111922] border border-[#233648] rounded-xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-[#233648] bg-[#16202a]">
                <th className="py-4 px-6 text-xs font-semibold text-gray-400 uppercase tracking-wider w-16">Rank</th>
                <th className="py-4 px-6 text-xs font-semibold text-gray-400 uppercase tracking-wider">Candidate</th>
                <th className="py-4 px-6 text-xs font-semibold text-gray-400 uppercase tracking-wider w-48">Match Score</th>
                <th className="py-4 px-6 text-xs font-semibold text-gray-400 uppercase tracking-wider w-32">Status</th>
                <th className="py-4 px-6 text-xs font-semibold text-gray-400 uppercase tracking-wider hidden md:table-cell">Key Skills Match</th>
                <th className="py-4 px-6 text-xs font-semibold text-gray-400 uppercase tracking-wider w-24 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#233648]">
              {filteredCandidates.map((candidate, index) => {
                const status = getStatus(candidate.score);
                const isExpanded = expandedRow === (candidate.id || String(index));
                const initials = candidate.name.split(' ').map(n => n[0]).slice(0, 2).join('');
                const rowId = candidate.id || String(index);

                return (
                  <React.Fragment key={rowId}>
                    <tr 
                      ref={el => { rowRefs.current[rowId] = el }}
                      className={`group transition-colors cursor-pointer ${isExpanded ? 'bg-[#1c2a3a]' : 'hover:bg-[#1c2a3a]/50'}`}
                      onClick={() => toggleRow(rowId)}
                    >
                      <td className="py-4 px-6 text-gray-500 font-medium">
                        #{index + 1}
                      </td>
                      <td className="py-4 px-6">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-full bg-[#233648] flex items-center justify-center text-sm font-bold text-gray-300 border border-[#324d67]">
                            {initials}
                          </div>
                          <div>
                            <button 
                                onClick={(e) => {
                                    e.stopPropagation(); // Prevent double toggle event if necessary, though logic handles it
                                    toggleRow(rowId);
                                }}
                                className="font-bold text-primary hover:underline text-sm text-left"
                            >
                                {candidate.name}
                            </button>
                            {/* Using summary snippet as role placeholder since we don't have strict role field */}
                            <div className="text-xs text-gray-500 truncate max-w-[200px]">Candidate</div> 
                          </div>
                        </div>
                      </td>
                      <td className="py-4 px-6">
                        <div className="flex items-center gap-3">
                          <div className="flex-1 h-1.5 bg-[#233648] rounded-full overflow-hidden">
                            <div 
                              className={`h-full rounded-full ${candidate.score >= 80 ? 'bg-emerald-500' : candidate.score >= 60 ? 'bg-yellow-500' : 'bg-red-500'}`} 
                              style={{ width: `${candidate.score}%` }}
                            ></div>
                          </div>
                          <span className={`text-sm font-bold ${candidate.score >= 80 ? 'text-emerald-400' : candidate.score >= 60 ? 'text-yellow-400' : 'text-red-400'}`}>
                            {candidate.score}
                          </span>
                        </div>
                        {/* Granular Scores if available */}
                         <div className="flex gap-4 mt-1">
                            {candidate.experienceScore !== undefined && (
                                <div className="flex items-center gap-1" title={`Experience Score: ${candidate.experienceScore}/100`}>
                                    <span className="text-[10px] text-gray-500 uppercase">Exp</span>
                                    <div className="w-8 h-1 bg-[#233648] rounded-full overflow-hidden">
                                        <div className="h-full bg-blue-500" style={{ width: `${candidate.experienceScore}%` }}></div>
                                    </div>
                                </div>
                            )}
                            {candidate.skillsScore !== undefined && (
                                <div className="flex items-center gap-1" title={`Skills Score: ${candidate.skillsScore}/100`}>
                                    <span className="text-[10px] text-gray-500 uppercase">Skill</span>
                                    <div className="w-8 h-1 bg-[#233648] rounded-full overflow-hidden">
                                        <div className="h-full bg-purple-500" style={{ width: `${candidate.skillsScore}%` }}></div>
                                    </div>
                                </div>
                            )}
                         </div>
                      </td>
                      <td className="py-4 px-6">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded text-xs font-medium border ${status.color}`}>
                          {status.label}
                        </span>
                      </td>
                      <td className="py-4 px-6 hidden md:table-cell">
                        <div className="flex flex-wrap gap-2">
                          {candidate.pros.slice(0, 3).map((skill, idx) => (
                            <span key={idx} className="px-2 py-1 rounded bg-[#233648] text-gray-300 text-xs border border-[#324d67]">
                              {skill.length > 20 ? skill.substring(0, 20) + '...' : skill}
                            </span>
                          ))}
                          {candidate.pros.length > 3 && (
                            <span className="px-2 py-1 rounded bg-[#233648] text-gray-400 text-xs border border-[#324d67]">
                              +{candidate.pros.length - 3}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="py-4 px-6 text-right">
                        <span className={`material-symbols-outlined text-gray-500 transition-transform duration-300 ${isExpanded ? 'rotate-180' : ''}`}>
                          expand_more
                        </span>
                      </td>
                    </tr>
                    
                    {/* Expanded Details Row */}
                    {isExpanded && (
                      <tr className="bg-[#16202a] border-b border-[#233648]">
                        <td colSpan={6} className="p-0">
                          <div className="p-6 grid grid-cols-1 md:grid-cols-3 gap-8 animate-fade-in">
                            
                            {/* Verdict & Notes - New Section from detailed_analysis */}
                            {candidate.detailedAnalysis && (
                                <div className="col-span-1 md:col-span-3 grid grid-cols-1 md:grid-cols-2 gap-6 bg-[#1c2a3a] p-4 rounded-lg border border-[#233648] mb-2">
                                    <div>
                                        <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">Final Verdict</h4>
                                        <span className={`inline-block px-3 py-1 rounded text-sm font-bold mb-2 ${
                                            candidate.detailedAnalysis.final_verdict.decision.includes('Hire') 
                                            ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' 
                                            : 'bg-red-500/20 text-red-400 border border-red-500/30'
                                        }`}>
                                            {candidate.detailedAnalysis.final_verdict.decision}
                                        </span>
                                        <p className="text-sm text-gray-300 leading-relaxed italic">
                                            "{candidate.detailedAnalysis.final_verdict.main_argument}"
                                        </p>
                                    </div>
                                    <div>
                                        <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">Hiring Manager Notes</h4>
                                        <div className="p-3 bg-[#111922] rounded border border-[#233648]">
                                            <p className="text-sm text-gray-400 leading-relaxed">
                                                {candidate.detailedAnalysis.final_verdict.hiring_manager_notes}
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* Highlights */}
                            <div>
                              <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">Highlights</h4>
                              <ul className="space-y-2">
                                {candidate.pros.map((pro, idx) => (
                                  <li key={idx} className="text-sm text-gray-300 flex items-start gap-2">
                                    <span className="material-symbols-outlined text-emerald-500 text-[16px] mt-0.5 shrink-0">check_circle</span>
                                    <span>{pro}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>

                            {/* Risks */}
                            <div>
                              <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">Risks & Flags</h4>
                              {candidate.cons.length > 0 ? (
                                <ul className="space-y-2">
                                  {candidate.cons.map((con, idx) => (
                                    <li key={idx} className="text-sm text-gray-300 flex items-start gap-2">
                                      <span className="material-symbols-outlined text-yellow-500 text-[16px] mt-0.5 shrink-0">warning</span>
                                      <span>{con}</span>
                                    </li>
                                  ))}
                                </ul>
                              ) : (
                                <p className="text-sm text-gray-500 italic">No significant risks identified.</p>
                              )}
                            </div>

                            {/* Notes / Summary (Fallback or Additional) */}
                            <div className="flex flex-col h-full">
                              <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">AI Summary</h4>
                              <p className="text-sm text-gray-300 leading-relaxed mb-4 flex-grow">
                                {candidate.summary}
                              </p>
                              
                              {candidate.fileName && (
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    window.open(`${API_BASE_URL}/view-resume/${candidate.fileName}`, '_blank');
                                  }}
                                  className="self-start text-xs font-medium text-primary hover:text-blue-400 flex items-center gap-1 mt-auto"
                                >
                                  <span className="material-symbols-outlined text-[16px]">open_in_new</span>
                                  View Original Resume
                                </button>
                              )}
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })}

              {filteredCandidates.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-gray-500">
                    <div className="flex flex-col items-center gap-2">
                      <span className="material-symbols-outlined text-4xl opacity-50">search_off</span>
                      <p>No candidates found matching your criteria.</p>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default ResultsSection;
