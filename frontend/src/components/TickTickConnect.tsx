import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  CheckCircle2,
  Circle,
  Link2,
  Calendar,
  Shield,
  Loader2,
  AlertCircle,
} from "lucide-react";
import {
  getTickTickStatus,
  connectTickTick,
  disconnectTickTick,
  type TickTickStatusResponse,
} from "../api";
import { cn } from "@/lib/utils";

export default function TickTickConnect() {
  const [status, setStatus] = useState<TickTickStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [disconnecting, setDisconnecting] = useState(false);

  const loadStatus = async () => {
    try {
      setLoading(true);
      setError(null);
      const statusData = await getTickTickStatus();
      setStatus(statusData);
    } catch (err) {
      setError("Failed to load TickTick status");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStatus();

    // Check for OAuth callback parameters
    const params = new URLSearchParams(window.location.search);
    const ticktickStatus = params.get("ticktick");

    if (ticktickStatus === "connected") {
      // Clear URL parameters
      window.history.replaceState({}, document.title, window.location.pathname);
      // Reload status to show connected state
      setTimeout(() => loadStatus(), 500);
    } else if (ticktickStatus === "error") {
      const message = params.get("message") || "Connection failed";
      setError(message);
      // Clear URL parameters
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []);

  const handleConnect = () => {
    connectTickTick(); // This will redirect
  };

  const handleDisconnect = async () => {
    if (!confirm("Are you sure you want to disconnect TickTick?")) {
      return;
    }

    try {
      setDisconnecting(true);
      setError(null);
      await disconnectTickTick();
      await loadStatus(); // Reload status
    } catch (err) {
      setError("Failed to disconnect TickTick");
    } finally {
      setDisconnecting(false);
    }
  };

  if (loading) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="bg-gradient-to-br from-black-soft to-black border-2 border-gold/30 rounded-xl p-6"
      >
        <div className="flex items-center justify-center gap-3 text-bone py-8">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
          >
            <Loader2 size={24} />
          </motion.div>
          <span>Loading TickTick status...</span>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-gradient-to-br from-black-soft to-black border-2 border-gold/30 rounded-xl p-6 space-y-6"
    >
      <div className="space-y-2">
        <h3 className="text-xl font-display font-bold text-bone flex items-center gap-2">
          <span>🎯</span> TickTick Integration
        </h3>
        <p className="text-sm text-bone-dim">
          Automatically sync extracted TODOs to your TickTick account
        </p>
      </div>

      {error && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
          className="flex items-center gap-2 p-3 bg-red-500/20 border border-red-500/30 rounded-lg text-red-500 text-sm"
        >
          <AlertCircle size={18} />
          {error}
        </motion.div>
      )}

      {status?.connected ? (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="space-y-6"
        >
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-green/20 border-2 border-green rounded-full text-green font-medium">
            <CheckCircle2 size={20} />
            <span>Connected</span>
          </div>

          <div className="space-y-3 bg-black/30 border border-bone-dim/20 rounded-lg p-4">
            <div className="flex items-center justify-between text-sm">
              <span className="text-bone-dim flex items-center gap-2">
                <Link2 size={16} />
                User ID:
              </span>
              <span className="text-bone font-medium">{status.user_id}</span>
            </div>
            {status.expires_at && (
              <div className="flex items-center justify-between text-sm">
                <span className="text-bone-dim flex items-center gap-2">
                  <Calendar size={16} />
                  Token Expires:
                </span>
                <span className="text-bone font-medium">
                  {new Date(status.expires_at).toLocaleDateString()}
                </span>
              </div>
            )}
            {status.scope && (
              <div className="flex items-center justify-between text-sm">
                <span className="text-bone-dim flex items-center gap-2">
                  <Shield size={16} />
                  Permissions:
                </span>
                <span className="text-bone font-medium">{status.scope}</span>
              </div>
            )}
          </div>

          <motion.button
            className={cn(
              "w-full px-4 py-2 rounded-lg font-medium transition-all flex items-center justify-center gap-2",
              disconnecting
                ? "bg-black-soft text-bone-dim cursor-not-allowed"
                : "border-2 border-red-500/30 text-red-500 hover:bg-red-500/10",
            )}
            onClick={handleDisconnect}
            disabled={disconnecting}
            whileHover={!disconnecting ? { scale: 1.02 } : {}}
            whileTap={!disconnecting ? { scale: 0.98 } : {}}
          >
            {disconnecting ? (
              <>
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                >
                  <Loader2 size={18} />
                </motion.div>
                Disconnecting...
              </>
            ) : (
              <>Disconnect TickTick</>
            )}
          </motion.button>
        </motion.div>
      ) : (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="space-y-6"
        >
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-bone-dim/10 border-2 border-bone-dim/30 rounded-full text-bone-dim font-medium">
            <Circle size={20} />
            <span>Not Connected</span>
          </div>

          <div className="space-y-3 bg-gold/10 border border-gold/30 rounded-lg p-4">
            <h4 className="text-sm font-display font-semibold text-gold">
              Benefits:
            </h4>
            <ul className="space-y-2 text-sm text-bone-dim">
              <li className="flex items-start gap-2">
                <span className="text-gold mt-0.5">•</span>
                <span>Auto-sync extracted TODOs to TickTick</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-gold mt-0.5">•</span>
                <span>Keep tasks organized in one place</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-gold mt-0.5">•</span>
                <span>Never miss an action item from meetings</span>
              </li>
            </ul>
          </div>

          <motion.button
            className="w-full px-4 py-2 bg-gradient-blue text-bone rounded-lg font-medium hover:shadow-lg hover:shadow-blue/50 transition-all flex items-center justify-center gap-2"
            onClick={handleConnect}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            <Link2 size={18} />
            Connect TickTick
          </motion.button>

          {status?.error && (
            <div className="text-xs text-red-500 text-center p-2 bg-red-500/10 rounded-lg border border-red-500/20">
              {status.error}
            </div>
          )}
        </motion.div>
      )}
    </motion.div>
  );
}
