import { useEffect, useMemo, useState } from "react";
import axios from "axios";
import { motion } from "framer-motion";
import { AlertTriangle, Calendar, Loader2, RefreshCcw, Sparkles } from "lucide-react";

import {
  JourneyCadence,
  JourneyPreference,
  JourneyPreferenceUpdateRequest,
  JourneyReport,
  fetchJourneyPreference,
  fetchJourneyReports,
  triggerJourneyReport,
  updateJourneyPreference,
} from "@/api";
import { Button } from "./ui/button";
import { StatusBadge } from "./ui/status-badge";
import LoadingSpinner from "./LoadingSpinner";
import { cn } from "@/lib/utils";
import { TIMEZONE_OPTIONS } from "@/data/timezones";

const cadenceOptions: { value: JourneyCadence; label: string }[] = [
  { value: "daily", label: "Daily" },
  { value: "weekly", label: "Weekly" },
  { value: "biweekly", label: "Bi-Weekly" },
  { value: "monthly", label: "Monthly" },
  { value: "quarterly", label: "Quarterly" },
  { value: "yearly", label: "Yearly" },
];

interface FormState {
  cadence: JourneyCadence;
  timezone: string;
  is_active: boolean;
}

function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  return date.toLocaleString();
}

function formatPeriod(start: string, end: string): string {
  const startDate = new Date(start);
  const endDate = new Date(end);
  return `${startDate.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  })} → ${endDate.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  })}`;
}

function mapStatus(status: JourneyReport["status"]): { badge: "completed" | "processing" | "pending" | "error"; label: string } {
  switch (status) {
    case "completed":
      return { badge: "completed", label: "Completed" };
    case "in_progress":
      return { badge: "processing", label: "Generating" };
    case "failed":
      return { badge: "error", label: "Failed" };
    default:
      return { badge: "pending", label: "Pending" };
  }
}

export default function JourneysView() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [featureAvailable, setFeatureAvailable] = useState(true);

  const [preference, setPreference] = useState<JourneyPreference | null>(null);
  const [formState, setFormState] = useState<FormState | null>(null);
  const [savingPreference, setSavingPreference] = useState(false);

  const [reports, setReports] = useState<JourneyReport[]>([]);
  const [totalReports, setTotalReports] = useState(0);
  const [refreshingReports, setRefreshingReports] = useState(false);
  const [generatingReport, setGeneratingReport] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const activeCadenceLabel = useMemo(() => {
    if (!preference) return "";
    return cadenceOptions.find((option) => option.value === preference.cadence)?.label ?? preference.cadence;
  }, [preference]);

  const loadReports = async () => {
    const reportList = await fetchJourneyReports();
    setReports(reportList.reports);
    setTotalReports(reportList.total);
  };

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const pref = await fetchJourneyPreference();
      setPreference(pref);
      setFormState({
        cadence: pref.cadence,
        timezone: pref.timezone ?? "UTC",
        is_active: pref.is_active,
      });

      await loadReports();
      setFeatureAvailable(true);
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.status === 404) {
        setFeatureAvailable(false);
        setError(null);
      } else {
        setError("Failed to load Journeys data. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handlePreferenceChange = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setFormState((prev) => (prev ? { ...prev, [key]: value } : prev));
  };

  const handleSavePreference = async () => {
    if (!formState) return;
    setSavingPreference(true);
    setStatusMessage(null);
    const payload: JourneyPreferenceUpdateRequest = {
      cadence: formState.cadence,
      timezone: formState.timezone,
      is_active: formState.is_active,
    };

    try {
      const updated = await updateJourneyPreference(payload);
      setPreference(updated);
      setFormState({
        cadence: updated.cadence,
        timezone: updated.timezone,
        is_active: updated.is_active,
      });
      setStatusMessage("Preferences saved successfully.");
    } catch (err) {
      setStatusMessage("Failed to save preferences. Please try again.");
    } finally {
      setSavingPreference(false);
    }
  };

  const refreshReports = async () => {
    setRefreshingReports(true);
    try {
      await loadReports();
    } catch (err) {
      setStatusMessage("Unable to refresh reports right now.");
    } finally {
      setRefreshingReports(false);
    }
  };

  const handleGenerateReport = async () => {
    setGeneratingReport(true);
    setStatusMessage(null);
    try {
      await triggerJourneyReport({ cadence: formState?.cadence ?? preference?.cadence });
      setStatusMessage("Report generation started. It will appear here once ready.");
      await loadReports();
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.status === 422) {
        setStatusMessage("Invalid report window requested. Check your preferences and try again.");
      } else {
        setStatusMessage("Failed to trigger report generation. Please try again.");
      }
    } finally {
      setGeneratingReport(false);
    }
  };

  if (!featureAvailable) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-4xl mx-auto px-4 py-12"
      >
        <div className="border border-gold/20 rounded-xl bg-black-soft/60 p-8 text-center space-y-4">
          <AlertTriangle className="mx-auto text-gold" size={36} />
          <h2 className="text-2xl font-semibold text-bone">Journeys Coming Soon</h2>
          <p className="text-bone-dim">
            The Journeys feature isn&apos;t enabled yet for this environment. Once it&apos;s turned on, you&apos;ll
            see your longitudinal reports here.
          </p>
        </div>
      </motion.div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <LoadingSpinner message="Loading your Journeys..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-12">
        <div className="border border-red-500/40 bg-red-500/10 text-red-100 rounded-lg p-6 space-y-3">
          <h2 className="text-xl font-semibold">Something went wrong</h2>
          <p>{error}</p>
          <Button onClick={loadData} variant="secondary">Retry</Button>
        </div>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-6xl mx-auto px-4 py-10 space-y-8"
    >
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-bone">Journeys</h1>
          <p className="text-bone-dim">
            Monitor how your conversations evolve over time and stay on top of the themes that matter.
          </p>
          {preference && (
            <p className="text-sm text-gold mt-2">
              Current cadence: <span className="font-semibold">{activeCadenceLabel}</span>
            </p>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            onClick={handleGenerateReport}
            disabled={generatingReport || !formState?.is_active}
            className="flex items-center"
          >
            {generatingReport ? (
              <Loader2 className="animate-spin" size={16} />
            ) : (
              <Sparkles size={16} />
            )}
            <span>Generate Report</span>
          </Button>
          <Button
            onClick={refreshReports}
            variant="ghost"
            disabled={refreshingReports}
            className="border border-gold/20"
          >
            {refreshingReports ? <Loader2 className="animate-spin" size={16} /> : <RefreshCcw size={16} />}
            <span>Refresh</span>
          </Button>
        </div>
      </div>

      {statusMessage && (
        <div className="border border-gold/30 bg-gold/10 text-gold px-4 py-3 rounded-lg">
          {statusMessage}
        </div>
      )}

      {formState && (
        <section className="border border-gold/20 rounded-xl bg-black-soft/40 p-6 space-y-6">
          <div className="flex items-center gap-2">
            <Calendar size={20} className="text-gold" />
            <h2 className="text-xl font-semibold text-bone">Preferences</h2>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            <label className="flex flex-col gap-2 text-sm text-bone">
              Cadence
              <select
                value={formState.cadence}
                onChange={(event) =>
                  handlePreferenceChange("cadence", event.target.value as JourneyCadence)
                }
                className="bg-black-soft border border-gold/20 rounded-md px-3 py-2 text-bone focus:outline-none focus:border-gold"
              >
                {cadenceOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="flex flex-col gap-2 text-sm text-bone">
              Timezone
              <select
                value={formState.timezone}
                onChange={(event) => handlePreferenceChange("timezone", event.target.value)}
                className="bg-black-soft border border-gold/20 rounded-md px-3 py-2 text-bone focus:outline-none focus:border-gold"
              >
                {TIMEZONE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="flex items-center gap-3 text-sm text-bone mt-8 md:mt-0">
              <input
                type="checkbox"
                checked={formState.is_active}
                onChange={(event) => handlePreferenceChange("is_active", event.target.checked)}
                className="h-4 w-4 accent-gold border border-gold/40 bg-black-soft"
              />
              Enable scheduled Journeys
            </label>
          </div>

          <div className="flex justify-end">
            <Button onClick={handleSavePreference} disabled={savingPreference}>
              {savingPreference ? <Loader2 className="animate-spin" size={16} /> : <span>Save Changes</span>}
            </Button>
          </div>
        </section>
      )}

      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-bone">Recent Reports</h2>
          <span className="text-sm text-bone-dim">{totalReports} total</span>
        </div>

        {reports.length === 0 ? (
          <div className="border border-gold/20 rounded-xl bg-black-soft/40 p-8 text-center text-bone-dim">
            No reports yet. Generate your first Journey to see a high-level view of your conversations.
          </div>
        ) : (
          <div className="space-y-4">
            {reports.map((report) => {
              const status = mapStatus(report.status);
              return (
                <div
                  key={report.id}
                  className={cn(
                    "border border-gold/15 rounded-xl bg-black-soft/30",
                    "p-5 hover:border-gold/40 transition-colors"
                  )}
                >
                  <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                    <div>
                      <h3 className="text-lg font-semibold text-bone capitalize">
                        {report.cadence} Journey • {formatPeriod(report.period_start, report.period_end)}
                      </h3>
                      <p className="text-sm text-bone-dim">
                        Generated at {formatDate(report.generated_at ?? report.updated_at)}
                      </p>
                    </div>
                    <StatusBadge status={status.badge} label={status.label} />
                  </div>

                  {report.summary && (
                    <p className="mt-4 text-bone-dim leading-relaxed">{report.summary}</p>
                  )}

                  <div className="mt-4 text-xs text-bone-dim">
                    <div>
                      <span className="font-semibold text-bone">From:</span> {formatDate(report.period_start)}
                    </div>
                    <div>
                      <span className="font-semibold text-bone">To:</span> {formatDate(report.period_end)}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </motion.div>
  );
}
