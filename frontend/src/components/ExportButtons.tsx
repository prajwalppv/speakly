import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Copy, Download, Check } from "lucide-react";
import { cn } from "@/lib/utils";

interface ExportButtonsProps {
  content: string;
  filename: string;
  type: "text" | "markdown";
  label?: string;
}

export default function ExportButtons({
  content,
  filename,
  type,
  label,
}: ExportButtonsProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      // Copy failed silently
    }
  };

  const handleDownload = () => {
    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${filename}.${type === "markdown" ? "md" : "txt"}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex items-center gap-2">
      {label && <span className="text-sm text-bone-dim">{label}</span>}
      <motion.button
        onClick={handleCopy}
        className={cn(
          "px-3 py-1.5 rounded-lg text-sm font-medium flex items-center gap-2 transition-all",
          copied
            ? "bg-green/20 text-green border border-green/30"
            : "bg-bone-dim/10 text-bone-dim border border-bone-dim/30 hover:bg-bone-dim/20",
        )}
        title="Copy to clipboard"
        aria-label="Copy to clipboard"
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
      >
        <AnimatePresence mode="wait">
          {copied ? (
            <motion.div
              key="check"
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              className="flex items-center gap-2"
            >
              <Check size={14} />
              <span>Copied!</span>
            </motion.div>
          ) : (
            <motion.div
              key="copy"
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              className="flex items-center gap-2"
            >
              <Copy size={14} />
              <span>Copy</span>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.button>
      <motion.button
        onClick={handleDownload}
        className="px-3 py-1.5 rounded-lg text-sm font-medium flex items-center gap-2 transition-all bg-blue/20 text-blue border border-blue/30 hover:bg-blue/30"
        title={`Download as ${type === "markdown" ? "Markdown" : "Text"}`}
        aria-label={`Download as ${type === "markdown" ? "Markdown" : "Text"}`}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
      >
        <Download size={14} />
        <span>Download</span>
      </motion.button>
    </div>
  );
}
