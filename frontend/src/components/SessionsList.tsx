import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { fetchSessions, SessionRecord } from '../api';
import TaskManager from './TaskManager';
import TranscriptEditor from './TranscriptEditor';
import ExportButtons from './ExportButtons';
import Tag from './Tag';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { 
  CheckCircle2, 
  Clock, 
  Pause, 
  XCircle, 
  FileText, 
  ChevronRight, 
  ChevronDown,
  ChevronLeft,
  MessageSquare,
  CheckSquare,
  RefreshCw,
  Sparkles,
  Link2,
  FolderOpen,
  Search,
  X as XIcon,
  Copy,
  Check,
  Filter,
  Loader2,
  AlertCircle,
  History,
  Edit2
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface ProcessingStage {
  status: string;
  timestamp: string | null;
}

interface SessionsListProps {
  refreshTrigger?: number; // Used to trigger refresh from parent
  searchQuery?: string; // External search query from command palette
  targetSessionId?: number | null; // Session to scroll to and expand
  onSearchApplied?: () => void; // Callback when search is applied
}

export default function SessionsList({ 
  refreshTrigger, 
  searchQuery: externalSearchQuery,
  targetSessionId,
  onSearchApplied 
}: SessionsListProps) {
  const [sessions, setSessions] = useState<SessionRecord[]>([]);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [selectedTags, setSelectedTags] = useState<string[]>([]); // Tag filter
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(10);
  const [copiedSummaryId, setCopiedSummaryId] = useState<number | null>(null);

  // Apply external search query from command palette
  useEffect(() => {
    if (externalSearchQuery) {
      setSearchQuery(externalSearchQuery);
      onSearchApplied?.();
    }
  }, [externalSearchQuery, onSearchApplied]);

  // Navigate to target session
  useEffect(() => {
    if (targetSessionId) {
      setExpandedId(targetSessionId);
      // Scroll to session
      setTimeout(() => {
        const element = document.querySelector(`[data-session-id="${targetSessionId}"]`);
        element?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }, 100);
      onSearchApplied?.();
    }
  }, [targetSessionId, onSearchApplied]);

  const loadSessions = async () => {
    try {
      const data = await fetchSessions();
      setSessions(data);
    } catch (error) {
      // Failed to load - UI will show empty state
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSessions();
  }, [refreshTrigger]);

  // Smart polling: Only poll sessions that are actively processing
  useEffect(() => {
    const hasProcessing = sessions.some(s => 
      s.status === 'processing' || s.status === 'pending'
    );

    if (!hasProcessing) {
      // No processing sessions - stop polling
      return;
    }

    const interval = setInterval(() => {
      loadSessions();
    }, 3000); // Poll every 3 seconds only when needed

    return () => clearInterval(interval);
  }, [sessions.map(s => `${s.id}:${s.status}`).join(',')]);

  const toggleExpand = (id: number) => {
    setExpandedId(expandedId === id ? null : id);
  };

  const handleCopySummary = async (e: React.MouseEvent, session: SessionRecord) => {
    e.stopPropagation(); // Don't expand the card
    if (!session.summary?.text) return;
    
    try {
      await navigator.clipboard.writeText(session.summary.text);
      setCopiedSummaryId(session.id);
      setTimeout(() => setCopiedSummaryId(null), 2000);
    } catch (error) {
      // Copy failed silently
    }
  };

  const getCurrentStep = (session: SessionRecord) => {
    const steps = getProcessingSteps(session);
    const inProgressIndex = steps.findIndex(s => s.status === 'in_progress');
    if (inProgressIndex !== -1) return inProgressIndex + 1;
    const completedCount = steps.filter(s => s.status === 'completed').length;
    return completedCount;
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed': return '#10b981';
      case 'processing': return '#3b82f6';
      case 'pending': return '#f59e0b';
      case 'error': return '#ef4444';
      default: return '#6b7280';
    }
  };

  const getStatusIcon = (status: string) => {
    const iconProps = { size: 20, strokeWidth: 2 };
    switch (status.toLowerCase()) {
      case 'completed': return <CheckCircle2 {...iconProps} className="status-icon-completed" />;
      case 'processing': return <Clock {...iconProps} className="status-icon-processing" />;
      case 'pending': return <Pause {...iconProps} className="status-icon-pending" />;
      case 'error': return <XCircle {...iconProps} className="status-icon-error" />;
      default: return <FileText {...iconProps} />;
    }
  };

  const formatTime = (dateString: string) => {
    // Backend sends UTC timestamps without 'Z', so add it for correct parsing
    const utcDateString = dateString.endsWith('Z') ? dateString : dateString + 'Z';
    const date = new Date(utcDateString);
    const now = new Date();
    const timeStr = date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
    
    // Check if it's today
    const isToday = date.toDateString() === now.toDateString();
    if (isToday) return `Today at ${timeStr}`;
    
    // Check if it's yesterday
    const yesterday = new Date(now);
    yesterday.setDate(yesterday.getDate() - 1);
    if (date.toDateString() === yesterday.toDateString()) {
      return `Yesterday at ${timeStr}`;
    }
    
    // Check if it's within the last week
    const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));
    if (diffDays < 7) {
      const dayName = date.toLocaleDateString('en-US', { weekday: 'long' });
      return `${dayName} at ${timeStr}`;
    }
    
    // Older: show date and time
    const dateStr = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    return `${dateStr} at ${timeStr}`;
  };

  const getSessionTitle = (session: SessionRecord) => {
    if (session.description) return session.description;
    if (session.transcriptions[0]?.text) {
      return session.transcriptions[0].text.substring(0, 80) + '...';
    }
    return `Session #${session.id}`;
  };

  const getProcessingSteps = (session: SessionRecord) => {
    const stages: Record<string, ProcessingStage> = (session as any).processing_stages || {};
    return [
      { key: 'uploaded', label: 'Upload', icon: '📤' },
      { key: 'transcribing', label: 'Transcribe', icon: '🎙️' },
      { key: 'diarizing', label: 'Diarize', icon: '👥' },
      { key: 'summarizing', label: 'Summarize', icon: '📝' },
      { key: 'extracting_tasks', label: 'Extract Tasks', icon: '✅' },
      { key: 'syncing_tasks', label: 'Sync', icon: '🔄' },
    ].map(step => ({
      ...step,
      status: stages[step.key]?.status || 'pending'
    }));
  };

  // Handle tag click
  const handleTagClick = (tagName: string, event: React.MouseEvent) => {
    event.stopPropagation(); // Prevent card expansion
    setSelectedTags(prev => 
      prev.includes(tagName) 
        ? prev.filter(t => t !== tagName) // Remove if already selected
        : [...prev, tagName] // Add if not selected
    );
    resetPagination();
  };

  // Clear tag filters
  const clearTagFilters = () => {
    setSelectedTags([]);
    resetPagination();
  };

  // Filter and search sessions
  const filteredSessions = sessions.filter(session => {
    // Status filter
    if (statusFilter !== 'all' && session.status !== statusFilter) {
      return false;
    }

    // Tag filter - session must have ALL selected tags
    if (selectedTags.length > 0) {
      const sessionTagNames = session.tags?.map(t => t.name) || [];
      const hasAllTags = selectedTags.every(tag => sessionTagNames.includes(tag));
      if (!hasAllTags) {
        return false;
      }
    }

    // Search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      const title = getSessionTitle(session).toLowerCase();
      const transcriptText = session.transcriptions[0]?.text?.toLowerCase() || '';
      const summaryText = session.summary?.text?.toLowerCase() || '';
      const description = session.description?.toLowerCase() || '';

      return (
        title.includes(query) ||
        transcriptText.includes(query) ||
        summaryText.includes(query) ||
        description.includes(query) ||
        `#${session.id}`.includes(query)
      );
    }

    return true;
  });

  // Pagination calculations
  const totalPages = Math.ceil(filteredSessions.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const paginatedSessions = filteredSessions.slice(startIndex, endIndex);

  // Reset to page 1 when filters change
  const resetPagination = () => {
    setCurrentPage(1);
  };

  if (loading) {
    return (
      <div className="w-full max-w-7xl mx-auto px-4 py-6">
        <h2 className="text-2xl font-display font-bold bg-gradient-gold bg-clip-text text-transparent mb-6">
          Your Recordings
        </h2>
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex items-center justify-center gap-3 text-bone py-12"
        >
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
          >
            <Loader2 size={24} />
          </motion.div>
          <span>Loading your recordings...</span>
        </motion.div>
      </div>
    );
  }

  if (sessions.length === 0) {
    return (
      <div className="w-full max-w-7xl mx-auto px-4 py-6">
        <h2 className="text-2xl font-display font-bold bg-gradient-gold bg-clip-text text-transparent mb-6">
          Your Recordings
        </h2>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-gradient-to-br from-black-soft to-black border-2 border-gold/30 rounded-xl p-12 text-center space-y-4"
        >
          <motion.div
            animate={{ scale: [1, 1.05, 1] }}
            transition={{ duration: 2, repeat: Infinity }}
          >
            <FolderOpen size={48} className="mx-auto text-gold" strokeWidth={1.5} />
          </motion.div>
          <p className="text-lg font-medium text-bone">No recordings yet</p>
          <p className="text-sm text-bone-dim max-w-md mx-auto">Upload your first audio file above to get AI-powered transcription, summaries, and action items!</p>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-7xl mx-auto px-4 py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-display font-bold bg-gradient-gold bg-clip-text text-transparent">
          Your Recordings
        </h2>
        <span className="text-sm text-bone-dim">
          {filteredSessions.length} of {sessions.length} {sessions.length === 1 ? 'recording' : 'recordings'}
        </span>
      </div>

      {/* Search and Filter Controls */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="flex-1 relative">
          <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-bone-dim" />
          <input
            type="text"
            placeholder="Search recordings, transcripts, or summaries..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              resetPagination();
            }}
            className="w-full pl-10 pr-10 py-2 bg-black border-2 border-gold/20 rounded-lg text-bone text-sm focus:outline-none focus:border-gold focus:ring-2 focus:ring-gold/20"
          />
          <AnimatePresence>
            {searchQuery && (
              <motion.button
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
                onClick={() => setSearchQuery('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-bone-dim hover:text-bone rounded-full hover:bg-white/10"
                aria-label="Clear search"
              >
                <XIcon size={16} />
              </motion.button>
            )}
          </AnimatePresence>
        </div>

        <div className="flex items-center gap-2">
          <Filter size={16} className="text-gold" />
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              resetPagination();
            }}
            className="px-4 py-2 bg-black border-2 border-gold/20 rounded-lg text-bone text-sm focus:outline-none focus:border-gold focus:ring-2 focus:ring-gold/20 cursor-pointer"
          >
            <option value="all">All Status</option>
            <option value="completed">Completed</option>
            <option value="processing">Processing</option>
            <option value="pending">Pending</option>
            <option value="error">Error</option>
          </select>
        </div>
      </div>

      {/* Active Tag Filters */}
      <AnimatePresence>
        {selectedTags.length > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="flex flex-wrap items-center gap-2 p-4 bg-gold/10 border border-gold/30 rounded-lg"
          >
            <span className="text-sm font-medium text-gold flex items-center gap-2">
              <Filter size={14} />
              Filtering by tags:
            </span>
            {selectedTags.map(tagName => (
              <motion.span
                key={tagName}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
                className="inline-flex items-center gap-1.5 px-3 py-1 bg-gold/20 border border-gold/30 text-gold rounded-full text-sm font-medium"
              >
                {tagName}
                <motion.button
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelectedTags(prev => prev.filter(t => t !== tagName));
                    resetPagination();
                  }}
                  className="hover:bg-gold/20 rounded-full p-0.5"
                  aria-label={`Remove ${tagName} filter`}
                  whileHover={{ scale: 1.1 }}
                  whileTap={{ scale: 0.9 }}
                >
                  <XIcon size={14} />
                </motion.button>
              </motion.span>
            ))}
            <motion.button
              onClick={clearTagFilters}
              className="ml-auto px-3 py-1 text-sm font-medium text-bone-dim hover:text-bone hover:bg-white/5 rounded-lg transition-colors"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              Clear all
            </motion.button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Sessions List */}
      <div className="space-y-3">
        {paginatedSessions.map((session) => {
          const isExpanded = expandedId === session.id;
          const hasTranscript = session.transcriptions[0]?.text;
          const hasSummary = session.summary?.text;

          return (
            <motion.div
              key={session.id}
              data-session-id={session.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.05 }}
              className={cn(
                "bg-gradient-to-br from-black-soft to-black border-2 rounded-xl overflow-hidden cursor-pointer transition-all",
                isExpanded ? "border-gold/50 shadow-lg shadow-gold/20" : "border-gold/20 hover:border-gold/30"
              )}
            >
              {/* Compact view */}
              <div 
                className="p-4 flex items-start gap-4"
                onClick={() => toggleExpand(session.id)}
              >
                <div className="flex-1 min-w-0 space-y-2">
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">{getStatusIcon(session.status)}</span>
                    <h3 className="text-lg font-display font-semibold text-bone truncate">{getSessionTitle(session)}</h3>
                  </div>
                  <div className="flex items-center gap-3 flex-wrap">
                    <span className="text-xs text-bone-dim flex items-center gap-1">
                      <Clock size={12} />
                      {formatTime(session.created_at)}
                    </span>
                    
                    {/* Tags */}
                    {session.tags && session.tags.length > 0 && (
                      <div className="flex items-center gap-1.5 flex-wrap">
                        {session.tags.slice(0, isExpanded ? session.tags.length : 3).map((tag) => (
                          <Tag 
                            key={tag.id} 
                            tag={tag} 
                            size="small"
                            onClick={(e) => handleTagClick(tag.name, e)}
                            isSelected={selectedTags.includes(tag.name)}
                          />
                        ))}
                        {!isExpanded && session.tags.length > 3 && (
                          <span className="text-xs text-gold px-2 py-0.5 bg-gold/20 rounded-full">
                            +{session.tags.length - 3} more
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <div className="flex flex-col items-end gap-2">
                    {hasSummary && !isExpanded && (
                      <motion.button
                        onClick={(e) => handleCopySummary(e, session)}
                        className={cn(
                          "px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all",
                          copiedSummaryId === session.id
                            ? "bg-green/20 text-green border border-green/30"
                            : "bg-blue/20 text-blue border border-blue/30 hover:bg-blue/30"
                        )}
                        title="Copy AI Summary to clipboard"
                        aria-label="Copy AI Summary"
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                      >
                        {copiedSummaryId === session.id ? (
                          <>
                            <Check size={14} />
                            <span>Copied!</span>
                          </>
                        ) : (
                          <>
                            <Copy size={14} />
                            <span>Copy Summary</span>
                          </>
                        )}
                      </motion.button>
                    )}
                    
                    {!isExpanded && (session.todo_count > 0 || session.todos.length > 0) && (
                      <span className="px-2 py-1 bg-green/20 text-green border border-green/30 rounded-full text-xs font-medium flex items-center gap-1.5">
                        <CheckSquare size={12} />
                        {session.todo_count || session.todos.length} {(session.todo_count || session.todos.length) === 1 ? 'action' : 'actions'}
                      </span>
                    )}
                  </div>
                  
                  <motion.button
                    className="p-2 text-gold hover:bg-gold/10 rounded-lg transition-colors"
                    animate={{ rotate: isExpanded ? 90 : 0 }}
                  >
                    <ChevronRight size={20} />
                  </motion.button>
                </div>
              </div>

              {/* Expanded details */}
              <AnimatePresence>
                {isExpanded && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="border-t border-gold/20 bg-black/30 p-6 space-y-6"
                    onClick={(e) => e.stopPropagation()}
                  >
                    {/* Error display */}
                    {session.last_error && (
                      <div className="flex items-center gap-2 p-3 bg-red-500/20 border border-red-500/30 rounded-lg text-red-500 text-sm">
                        <AlertCircle size={18} />
                        {session.last_error}
                      </div>
                    )}

                    {/* Transcript */}
                    {hasTranscript && (
                      <div className="space-y-3">
                        <TranscriptEditor
                          transcriptionId={session.transcriptions[0].id}
                          initialText={session.transcriptions[0].text!}
                          onSave={async () => {
                            await loadSessions();
                          }}
                          renderActions={(actions) => (
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                <h4 className="text-sm font-display font-semibold text-bone">📝 Transcript</h4>
                                <motion.button
                                  className="px-2 py-1 border border-gold/30 text-gold rounded-lg text-xs font-medium hover:bg-gold/10 transition-colors disabled:opacity-50 flex items-center gap-1.5"
                                  onClick={actions.loadHistory}
                                  disabled={actions.loadingHistory}
                                  whileHover={{ scale: 1.05 }}
                                  whileTap={{ scale: 0.95 }}
                                >
                                  <History size={12} />
                                  {actions.loadingHistory ? 'Loading...' : 'History'}
                                </motion.button>
                                <motion.button
                                  className="px-2 py-1 bg-gradient-blue text-bone rounded-lg text-xs font-medium hover:shadow-lg hover:shadow-blue/50 transition-all flex items-center gap-1.5"
                                  onClick={actions.handleEdit}
                                  whileHover={{ scale: 1.05 }}
                                  whileTap={{ scale: 0.95 }}
                                >
                                  <Edit2 size={12} />
                                  Edit
                                </motion.button>
                              </div>
                              <ExportButtons
                                content={session.transcriptions[0].text!}
                                filename={`transcript-${session.id}`}
                                type="text"
                              />
                            </div>
                          )}
                        />
                      </div>
                    )}

                    {/* AI Summary */}
                    {hasSummary && session.summary && (
                      <div className="space-y-3">
                        <div className="flex items-center justify-between">
                          <h4 className="text-sm font-display font-semibold text-bone">✨ AI Summary</h4>
                          <ExportButtons
                            content={session.summary.text || ''}
                            filename={`summary-${session.id}`}
                            type="markdown"
                          />
                        </div>
                        <div className="prose prose-invert prose-sm max-w-none prose-headings:text-gold prose-a:text-blue prose-strong:text-bone prose-code:text-green">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {session.summary.text}
                          </ReactMarkdown>
                        </div>
                      </div>
                    )}

                    {/* Tasks */}
                    <TaskManager
                      sessionId={session.id}
                      todos={session.todos}
                      onUpdate={loadSessions}
                    />

                    {/* Metadata */}
                    <div className="flex items-center gap-4 pt-4 border-t border-bone-dim/20 text-xs text-bone-dim">
                      <span>ID: {session.id}</span>
                      <span>Created: {new Date(session.created_at).toLocaleString()}</span>
                      <span>Updated: {new Date(session.updated_at).toLocaleString()}</span>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          );
        })}
      </div>

      {/* Pagination Controls */}
      {filteredSessions.length > 0 && (
        <div className="flex items-center justify-between py-4">
          <div className="text-sm text-bone-dim">
            Showing {startIndex + 1}-{Math.min(endIndex, filteredSessions.length)} of {filteredSessions.length}
          </div>

          <div className="flex items-center gap-2">
            <motion.button
              onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
              disabled={currentPage === 1}
              className={cn(
                "p-2 rounded-lg border-2 transition-colors",
                currentPage === 1 
                  ? "border-bone-dim/20 text-bone-dim/50 cursor-not-allowed"
                  : "border-gold/30 text-gold hover:bg-gold/10"
              )}
              aria-label="Previous page"
              whileHover={currentPage !== 1 ? { scale: 1.05 } : {}}
              whileTap={currentPage !== 1 ? { scale: 0.95 } : {}}
            >
              <ChevronLeft size={18} />
            </motion.button>

            <div className="flex items-center gap-1">
              {Array.from({ length: totalPages }, (_, i) => i + 1).map(page => {
                if (
                  page === 1 ||
                  page === totalPages ||
                  (page >= currentPage - 1 && page <= currentPage + 1)
                ) {
                  return (
                    <motion.button
                      key={page}
                      onClick={() => setCurrentPage(page)}
                      className={cn(
                        "w-10 h-10 rounded-lg border-2 font-medium text-sm transition-colors",
                        page === currentPage
                          ? "border-gold bg-gold/20 text-gold"
                          : "border-bone-dim/20 text-bone-dim hover:border-gold/30 hover:text-gold"
                      )}
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                    >
                      {page}
                    </motion.button>
                  );
                } else if (
                  page === currentPage - 2 ||
                  page === currentPage + 2
                ) {
                  return <span key={page} className="px-2 text-bone-dim">...</span>;
                }
                return null;
              })}
            </div>

            <motion.button
              onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
              disabled={currentPage === totalPages}
              className={cn(
                "p-2 rounded-lg border-2 transition-colors",
                currentPage === totalPages
                  ? "border-bone-dim/20 text-bone-dim/50 cursor-not-allowed"
                  : "border-gold/30 text-gold hover:bg-gold/10"
              )}
              aria-label="Next page"
              whileHover={currentPage !== totalPages ? { scale: 1.05 } : {}}
              whileTap={currentPage !== totalPages ? { scale: 0.95 } : {}}
            >
              <ChevronRight size={18} />
            </motion.button>
          </div>

          <div className="flex items-center gap-2 text-sm">
            <label htmlFor="items-per-page" className="text-bone-dim">Per page:</label>
            <select
              id="items-per-page"
              value={itemsPerPage}
              onChange={(e) => {
                setItemsPerPage(Number(e.target.value));
                resetPagination();
              }}
              className="px-3 py-1.5 bg-black border-2 border-gold/20 rounded-lg text-bone focus:outline-none focus:border-gold focus:ring-2 focus:ring-gold/20 cursor-pointer"
            >
              <option value={10}>10</option>
              <option value={25}>25</option>
              <option value={50}>50</option>
            </select>
          </div>
        </div>
      )}
    </div>
  );
}
