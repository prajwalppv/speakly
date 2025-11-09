import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Search, Upload, FileText, Link2, ArrowRight } from "lucide-react";
import { SessionRecord } from "../api";
import { cn } from "@/lib/utils";

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  sessions: SessionRecord[];
  onUpload: () => void;
  onNavigateToSession: (sessionId: number) => void;
  onOpenIntegrations: () => void;
  onSearch: (query: string) => void;
}

interface Command {
  id: string;
  label: string;
  icon: React.ReactNode;
  action: () => void;
  keywords?: string[];
}

export default function CommandPalette({
  isOpen,
  onClose,
  sessions,
  onUpload,
  onNavigateToSession,
  onOpenIntegrations,
  onSearch,
}: CommandPaletteProps) {
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  // Static commands
  const staticCommands: Command[] = [
    {
      id: "upload",
      label: "Upload audio file",
      icon: <Upload size={18} />,
      action: () => {
        onUpload();
        onClose();
      },
      keywords: ["upload", "add", "new", "file", "audio"],
    },
    {
      id: "integrations",
      label: "Manage TickTick integration",
      icon: <Link2 size={18} />,
      action: () => {
        onOpenIntegrations();
        onClose();
      },
      keywords: ["ticktick", "integration", "connect", "settings"],
    },
  ];

  // Generate commands from sessions
  const sessionCommands: Command[] = sessions.slice(0, 10).map((session) => ({
    id: `session-${session.id}`,
    label:
      session.description ||
      session.transcriptions[0]?.text?.substring(0, 60) ||
      `Recording #${session.id}`,
    icon: <FileText size={18} />,
    action: () => {
      onNavigateToSession(session.id);
      onClose();
    },
    keywords: [
      `#${session.id}`,
      session.description || "",
      session.transcriptions[0]?.text || "",
    ],
  }));

  // Filter commands based on query
  const filteredCommands = [...staticCommands, ...sessionCommands].filter(
    (cmd) => {
      if (!query.trim()) return true;

      const searchQuery = query.toLowerCase();
      const labelMatch = cmd.label.toLowerCase().includes(searchQuery);
      const keywordMatch = cmd.keywords?.some((k) =>
        k.toLowerCase().includes(searchQuery),
      );

      return labelMatch || keywordMatch;
    },
  );

  // Handle keyboard navigation
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((prev) =>
          Math.min(prev + 1, filteredCommands.length - 1),
        );
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((prev) => Math.max(prev - 1, 0));
      } else if (e.key === "Enter") {
        e.preventDefault();
        if (filteredCommands[selectedIndex]) {
          filteredCommands[selectedIndex].action();
        } else if (query.trim()) {
          // If no command selected but there's a query, trigger search
          onSearch(query);
          onClose();
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, selectedIndex, filteredCommands, query, onClose, onSearch]);

  // Reset when opened
  useEffect(() => {
    if (isOpen) {
      setQuery("");
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 10);
    }
  }, [isOpen]);

  // Reset selected index when query changes
  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50"
            onClick={onClose}
          />

          {/* Command Palette */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -20 }}
            transition={{ duration: 0.2 }}
            className="fixed top-[20%] left-1/2 -translate-x-1/2 w-full max-w-2xl z-50 bg-gradient-to-br from-black-soft to-black border-2 border-gold/30 rounded-xl shadow-2xl overflow-hidden"
          >
            {/* Header */}
            <div className="flex items-center gap-3 p-4 border-b border-bone-dim/20">
              <Search size={20} className="text-gold" />
              <input
                ref={inputRef}
                type="text"
                placeholder="Type a command or search..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="flex-1 bg-transparent text-bone placeholder:text-bone-dim focus:outline-none"
              />
              <kbd className="px-2 py-1 bg-black/50 border border-bone-dim/30 rounded text-xs text-bone-dim font-mono">
                ESC
              </kbd>
            </div>

            {/* Command List */}
            <div className="max-h-96 overflow-y-auto">
              {filteredCommands.length > 0 ? (
                filteredCommands.map((cmd, index) => (
                  <motion.button
                    key={cmd.id}
                    onClick={cmd.action}
                    onMouseEnter={() => setSelectedIndex(index)}
                    className={cn(
                      "w-full flex items-center justify-between p-4 text-left transition-colors group",
                      index === selectedIndex
                        ? "bg-gold/20 border-l-2 border-gold"
                        : "hover:bg-white/5",
                    )}
                    whileHover={{ x: 4 }}
                  >
                    <div className="flex items-center gap-3">
                      <span
                        className={cn(
                          "transition-colors",
                          index === selectedIndex
                            ? "text-gold"
                            : "text-bone-dim",
                        )}
                      >
                        {cmd.icon}
                      </span>
                      <span
                        className={cn(
                          "text-sm font-medium transition-colors",
                          index === selectedIndex
                            ? "text-bone"
                            : "text-bone-dim",
                        )}
                      >
                        {cmd.label}
                      </span>
                    </div>
                    <ArrowRight
                      size={16}
                      className={cn(
                        "transition-all",
                        index === selectedIndex
                          ? "text-gold opacity-100"
                          : "text-bone-dim opacity-0 group-hover:opacity-100",
                      )}
                    />
                  </motion.button>
                ))
              ) : (
                <div className="p-8 text-center space-y-4">
                  <p className="text-bone-dim">No commands found</p>
                  {query && (
                    <motion.button
                      onClick={() => {
                        onSearch(query);
                        onClose();
                      }}
                      className="px-4 py-2 bg-gradient-blue text-bone rounded-lg text-sm font-medium hover:shadow-lg hover:shadow-blue/50 transition-all"
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                    >
                      Search for "{query}"
                    </motion.button>
                  )}
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="flex items-center justify-center gap-6 p-3 border-t border-bone-dim/20 bg-black/30">
              <div className="flex items-center gap-1.5 text-xs text-bone-dim">
                <kbd className="px-1.5 py-0.5 bg-black border border-bone-dim/30 rounded font-mono">
                  ↑
                </kbd>
                <kbd className="px-1.5 py-0.5 bg-black border border-bone-dim/30 rounded font-mono">
                  ↓
                </kbd>
                <span>Navigate</span>
              </div>
              <div className="flex items-center gap-1.5 text-xs text-bone-dim">
                <kbd className="px-1.5 py-0.5 bg-black border border-bone-dim/30 rounded font-mono">
                  ↵
                </kbd>
                <span>Select</span>
              </div>
              <div className="flex items-center gap-1.5 text-xs text-bone-dim">
                <kbd className="px-1.5 py-0.5 bg-black border border-bone-dim/30 rounded font-mono">
                  ESC
                </kbd>
                <span>Close</span>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
