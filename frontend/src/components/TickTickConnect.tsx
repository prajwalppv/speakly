import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Link2, Calendar, Shield, Loader2, AlertCircle, X } from "lucide-react";
import {
  getTickTickStatus,
  connectTickTick,
  disconnectTickTick,
  type TickTickStatusResponse,
} from "../api";
import { cn } from "@/lib/utils";

interface TickTickConnectProps {
  className?: string;
}

export default function TickTickConnect({ className }: TickTickConnectProps) {
  const [status, setStatus] = useState<TickTickStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [disconnecting, setDisconnecting] = useState(false);
  const [connecting, setConnecting] = useState(false);

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
    if (connecting || status?.connected) return;
    setConnecting(true);
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

  const featurePills = [
    "Auto-sync TODOs",
    "Keep tasks in one place",
    "Never miss action items",
  ];

  const isConnected = Boolean(status?.connected);
  const featureSummary = featurePills.join(" • ");
  const connectedDetails = status?.connected
    ? ([
        status.user_id && { label: "User", value: status.user_id },
        status.expires_at && {
          label: "Expires",
          value: new Date(status.expires_at).toLocaleDateString(),
        },
        status.scope && { label: "Scope", value: status.scope },
      ].filter(Boolean) as Array<{ label: string; value: string }>)
    : [];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        "bg-gradient-to-br from-black-soft to-black border-2 border-gold/30 rounded-xl p-4 space-y-4",
        className,
      )}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-display font-semibold text-bone">
            Integrations
          </h3>
          <p className="text-xs text-bone-dim">
            Connect Speakly to your task managers.
          </p>
        </div>
        {loading && (
          <div className="flex items-center gap-2 text-xs text-bone-dim">
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
            >
              <Loader2 size={14} />
            </motion.div>
            Checking...
          </div>
        )}
      </div>

      {error && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
          className="flex items-center gap-2 p-3 bg-red-500/15 border border-red-500/30 rounded-lg text-red-400 text-xs"
        >
          <AlertCircle size={16} />
          {error}
        </motion.div>
      )}

      <div className="space-y-3">
        <div className="group rounded-xl border border-gold/20 bg-black/40 p-4 space-y-2 transition-colors focus-within:border-gold/40">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div
              className="flex items-center gap-3 min-w-0"
              title={featureSummary}
            >
              <div className="text-2xl leading-none">🎯</div>
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-semibold text-bone">
                    TickTick
                  </span>
                  <span
                    className={cn(
                      "px-2 py-0.5 rounded-full text-[11px] font-semibold flex items-center gap-1",
                      isConnected
                        ? "bg-green/15 text-green border border-green/40"
                        : "bg-bone-dim/10 text-bone-dim border border-bone-dim/30",
                    )}
                    aria-label={isConnected ? "Connected" : "Not connected"}
                    title={isConnected ? "Connected" : "Not connected"}
                  >
                    <span
                      className={cn(
                        "inline-block w-2 h-2 rounded-full",
                        isConnected
                          ? "bg-green shadow-[0_0_4px_rgba(74,222,128,0.9)]"
                          : "bg-red-500",
                      )}
                    />
                    <span className="sr-only">
                      {isConnected ? "Connected" : "Not connected"}
                    </span>
                  </span>
                </div>
                <p className="text-xs text-bone-dim line-clamp-1">
                  Sync TODOs into TickTick
                </p>
              </div>
            </div>
            <motion.button
              className={cn(
                "px-4 py-2 rounded-lg text-sm font-semibold border transition-all flex items-center gap-1.5 self-start md:self-auto",
                isConnected
                  ? "border-red-500/40 text-red-400 hover:bg-red-500/10"
                  : "border-gold/60 text-bone hover:bg-gold/10",
              )}
              onClick={isConnected ? handleDisconnect : handleConnect}
              disabled={
                loading ||
                connecting ||
                disconnecting ||
                (isConnected ? disconnecting : connecting)
              }
              whileHover={
                !loading && !(isConnected ? disconnecting : connecting)
                  ? { scale: 1.01 }
                  : {}
              }
              whileTap={
                !loading && !(isConnected ? disconnecting : connecting)
                  ? { scale: 0.99 }
                  : {}
              }
            >
              {isConnected ? (
                disconnecting ? (
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{
                      duration: 1,
                      repeat: Infinity,
                      ease: "linear",
                    }}
                  >
                    <Loader2 size={14} />
                  </motion.div>
                ) : (
                  <X size={14} />
                )
              ) : connecting ? (
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                >
                  <Loader2 size={14} />
                </motion.div>
              ) : (
                <Link2 size={14} />
              )}
              {isConnected ? "Disconnect" : "Connect"}
            </motion.button>
          </div>

          <div
            className={cn(
              "text-xs text-bone-dim transition-all duration-200 ease-out leading-relaxed",
              "max-h-0 opacity-0 group-hover:max-h-40 group-hover:opacity-80 group-focus-within:max-h-40 group-focus-within:opacity-80",
            )}
          >
            {isConnected ? (
              <div className="grid gap-2 sm:grid-cols-3 text-[11px] text-bone-dim">
                {connectedDetails.map(({ label, value }) => (
                  <div
                    key={label}
                    className="flex items-center gap-1.5 min-w-0"
                  >
                    <span>{label}:</span>
                    <span
                      className="text-bone font-semibold truncate"
                      title={value}
                    >
                      {value}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex flex-wrap gap-1.5 text-[11px]">
                {featurePills.map((text) => (
                  <span
                    key={text}
                    className="px-2.5 py-0.5 rounded-full border border-bone-dim/30 text-bone-dim"
                  >
                    {text}
                  </span>
                ))}
              </div>
            )}
          </div>

          {status?.error && (
            <div
              className={cn(
                "text-[11px] text-red-400 text-center p-2 bg-red-500/10 rounded-lg border border-red-500/20 transition-all duration-200",
                "max-h-0 opacity-0 group-hover:max-h-14 group-hover:opacity-100 group-focus-within:max-h-14 group-focus-within:opacity-100",
              )}
            >
              {status.error}
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}
