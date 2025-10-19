import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ShieldCheck, Eye, Loader2, AlertCircle } from "lucide-react";

import {
  fetchUserPreferences,
  updateUserPreferences,
  UserPreferences,
} from "@/api";

export default function RecordingPreferences() {
  const [preferences, setPreferences] = useState<UserPreferences | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const prefs = await fetchUserPreferences();
        setPreferences(prefs);
      } catch {
        setError("Failed to load recording preferences.");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const toggleAutoApprove = async () => {
    if (!preferences) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await updateUserPreferences({
        auto_approve_sessions: !preferences.auto_approve_sessions,
      });
      setPreferences(updated);
    } catch {
      setError("Unable to update preferences. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  const autoApproveEnabled = preferences?.auto_approve_sessions ?? false;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full bg-gradient-to-br from-black-soft to-black border-2 border-gold/30 rounded-xl p-6 space-y-4"
    >
      <div className="flex items-center justify-between gap-4">
        <div className="space-y-1">
          <h3 className="text-lg font-display font-semibold text-bone flex items-center gap-2">
            <ShieldCheck size={18} className="text-gold" />
            Recording Preferences
          </h3>
          <p className="text-sm text-bone-dim">
            Decide whether new recordings are stored automatically after
            processing, or if you want to review and approve them first.
          </p>
        </div>
        <motion.button
          onClick={toggleAutoApprove}
          disabled={loading || saving || !preferences}
          className="px-4 py-2 rounded-lg border-2 border-gold/40 text-sm font-semibold text-bone hover:bg-gold/10 transition-all flex items-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed"
          whileHover={!saving && !loading ? { scale: 1.03 } : {}}
          whileTap={!saving && !loading ? { scale: 0.97 } : {}}
        >
          {saving ? (
            <Loader2 size={16} className="animate-spin" />
          ) : autoApproveEnabled ? (
            <ShieldCheck size={16} />
          ) : (
            <Eye size={16} />
          )}
          <span>
            {autoApproveEnabled ? "Auto-approve on" : "Manual review on"}
          </span>
        </motion.button>
      </div>

      {loading && (
        <div className="flex items-center gap-2 text-sm text-bone-dim">
          <Loader2 size={16} className="animate-spin" />
          Loading your preferences...
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 text-sm text-red-300 bg-red-500/10 border border-red-500/30 px-3 py-2 rounded-lg">
          <AlertCircle size={16} />
          {error}
        </div>
      )}

      {!loading && (
        <ul className="text-sm text-bone-dim space-y-1 list-disc list-inside">
          <li>
            {autoApproveEnabled
              ? "New recordings are finalized automatically after processing."
              : "New recordings pause in review until you approve or discard them."}
          </li>
          <li>
            You can switch this setting anytime—existing recordings keep their
            current review status.
          </li>
        </ul>
      )}
    </motion.div>
  );
}
