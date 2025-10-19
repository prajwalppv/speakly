import { useEffect, useMemo, useState } from "react";
import axios from "axios";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  Calendar,
  Loader2,
  RefreshCcw,
  Sparkles,
  Trash2,
} from "lucide-react";

import {
  JourneyCadence,
  JourneyPreference,
  JourneyPreferenceUpdateRequest,
  JourneyReport,
  fetchJourneyPreference,
  fetchJourneyReports,
  triggerJourneyReport,
  deleteJourneyReport,
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
  email_enabled: boolean;
}

function formatDate(
  value: string | null | undefined,
  timeZone?: string,
  withTime: boolean = true,
): string {
  if (!value) return "—";
  const normalized =
    value.includes("Z") || value.includes("+") ? value : `${value}Z`;
  const date = new Date(normalized);
  const options: Intl.DateTimeFormatOptions = {
    month: "short",
    day: "numeric",
    year: "numeric",
  };
  if (timeZone) {
    options.timeZone = timeZone;
  }
  if (withTime) {
    options.hour = "2-digit";
    options.minute = "2-digit";
  }
  return new Intl.DateTimeFormat(undefined, options).format(date);
}

function formatPeriod(start: string, end: string, timeZone: string): string {
  const options: Intl.DateTimeFormatOptions = {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone,
  };
  const startDate = new Date(
    start.includes("Z") || start.includes("+") ? start : `${start}Z`,
  );
  const endDate = new Date(
    end.includes("Z") || end.includes("+") ? end : `${end}Z`,
  );
  return `${new Intl.DateTimeFormat(undefined, options).format(startDate)} → ${new Intl.DateTimeFormat(
    undefined,
    options,
  ).format(endDate)}`;
}

function mapStatus(status: JourneyReport["status"]): {
  badge: "completed" | "processing" | "pending" | "error";
  label: string;
} {
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
  const [deletingReportId, setDeletingReportId] = useState<number | null>(null);

  const activeCadenceLabel = useMemo(() => {
    if (!preference) return "";
    return (
      cadenceOptions.find((option) => option.value === preference.cadence)
        ?.label ?? preference.cadence
    );
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
        email_enabled: pref.email_enabled ?? true,
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

  const handlePreferenceChange = <K extends keyof FormState>(
    key: K,
    value: FormState[K],
  ) => {
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
      email_enabled: formState.email_enabled,
    };

    try {
      const updated = await updateJourneyPreference(payload);
      setPreference(updated);
      setFormState({
        cadence: updated.cadence,
        timezone: updated.timezone,
        is_active: updated.is_active,
        email_enabled: updated.email_enabled,
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
      await triggerJourneyReport({
        cadence: formState?.cadence ?? preference?.cadence,
      });
      setStatusMessage(
        "Report generation started. It will appear here once ready.",
      );
      await loadReports();
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.status === 422) {
        setStatusMessage(
          "Invalid report window requested. Check your preferences and try again.",
        );
      } else {
        setStatusMessage(
          "Failed to trigger report generation. Please try again.",
        );
      }
    } finally {
      setGeneratingReport(false);
    }
  };

  const handleDeleteReport = async (reportId: number) => {
    setDeletingReportId(reportId);
    try {
      await deleteJourneyReport(reportId);
      await loadReports();
    } catch (err) {
      setStatusMessage("Failed to delete report. Please try again.");
    } finally {
      setDeletingReportId(null);
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
          <h2 className="text-2xl font-semibold text-bone">
            Journeys Coming Soon
          </h2>
          <p className="text-bone-dim">
            The Journeys feature isn&apos;t enabled yet for this environment.
            Once it&apos;s turned on, you&apos;ll see your longitudinal reports
            here.
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
          <Button onClick={loadData} variant="secondary">
            Retry
          </Button>
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
            Monitor how your conversations evolve over time and stay on top of
            the themes that matter.
          </p>
          {preference && (
            <p className="text-sm text-gold mt-2">
              Current cadence:{" "}
              <span className="font-semibold">{activeCadenceLabel}</span>
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
            {refreshingReports ? (
              <Loader2 className="animate-spin" size={16} />
            ) : (
              <RefreshCcw size={16} />
            )}
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
                  handlePreferenceChange(
                    "cadence",
                    event.target.value as JourneyCadence,
                  )
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
                onChange={(event) =>
                  handlePreferenceChange("timezone", event.target.value)
                }
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
                onChange={(event) =>
                  handlePreferenceChange("is_active", event.target.checked)
                }
                className="h-4 w-4 accent-gold border border-gold/40 bg-black-soft"
              />
              Enable scheduled Journeys
            </label>
            <label className="flex items-center gap-3 text-sm text-bone mt-4 md:mt-0">
              <input
                type="checkbox"
                checked={formState.email_enabled}
                onChange={(event) =>
                  handlePreferenceChange("email_enabled", event.target.checked)
                }
                className="h-4 w-4 accent-gold border border-gold/40 bg-black-soft"
              />
              Email me each Journey report
            </label>
          </div>

          <div className="flex justify-end">
            <Button onClick={handleSavePreference} disabled={savingPreference}>
              {savingPreference ? (
                <Loader2 className="animate-spin" size={16} />
              ) : (
                <span>Save Changes</span>
              )}
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
            No reports yet. Generate your first Journey to see a high-level view
            of your conversations.
          </div>
        ) : (
          <div className="space-y-4">
            {reports.map((report) => {
              const status = mapStatus(report.status);
              const metrics = (report.payload as any)?.metrics;
              const sessions: any[] = (report.payload as any)?.sessions ?? [];
              const todosSummary: any = (report.payload as any)?.todos ?? {};
              const topTags: any[] =
                (report.payload as any)?.top_tags ?? metrics?.top_tags ?? [];
              const summaryParagraphs = report.summary
                ? report.summary.split(/\n+/).filter(Boolean)
                : [];
              const periodTimezone: string = metrics?.period?.timezone ?? "UTC";
              return (
                <div
                  key={report.id}
                  className={cn(
                    "border border-gold/15 rounded-xl bg-black-soft/30",
                    "p-5 hover:border-gold/40 transition-colors",
                  )}
                >
                  <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                    <div>
                      <h3 className="text-lg font-semibold text-bone capitalize">
                        {report.cadence} Journey •{" "}
                        {formatPeriod(
                          report.period_start,
                          report.period_end,
                          periodTimezone,
                        )}
                      </h3>
                      <p className="text-sm text-bone-dim">
                        Generated at{" "}
                        {formatDate(
                          report.generated_at ?? report.updated_at,
                          periodTimezone,
                          true,
                        )}
                      </p>
                    </div>
                    <StatusBadge status={status.badge} label={status.label} />
                    <Button
                      variant="ghost"
                      className="border border-gold/20 text-xs"
                      onClick={() => handleDeleteReport(report.id)}
                      disabled={deletingReportId === report.id}
                    >
                      {deletingReportId === report.id ? (
                        <Loader2 className="animate-spin" size={16} />
                      ) : (
                        <>
                          <Trash2 size={16} />
                          <span>Delete</span>
                        </>
                      )}
                    </Button>
                  </div>

                  {summaryParagraphs.length > 0 && (
                    <div className="mt-4 space-y-2 text-bone-dim leading-relaxed">
                      {summaryParagraphs.map((paragraph, index) => (
                        <p key={index}>{paragraph}</p>
                      ))}
                    </div>
                  )}

                  {metrics && (
                    <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                      <div className="rounded-lg border border-gold/15 bg-black-soft/50 p-4">
                        <p className="text-sm text-bone-dim">Sessions</p>
                        <p className="text-2xl font-semibold text-bone">
                          {metrics.sessions?.total ?? "—"}
                        </p>
                        <p className="text-xs text-bone-dim mt-1">
                          {metrics.sessions?.completed ?? 0} completed •{" "}
                          {metrics.sessions?.average_minutes ?? 0} avg min
                        </p>
                      </div>
                      <div className="rounded-lg border border-gold/15 bg-black-soft/50 p-4">
                        <p className="text-sm text-bone-dim">Listening Time</p>
                        <p className="text-2xl font-semibold text-bone">
                          {metrics.sessions?.total_minutes ?? 0}
                        </p>
                        <p className="text-xs text-bone-dim mt-1">
                          Total minutes processed
                        </p>
                      </div>
                      <div className="rounded-lg border border-gold/15 bg-black-soft/50 p-4">
                        <p className="text-sm text-bone-dim">Tasks</p>
                        <p className="text-2xl font-semibold text-bone">
                          {todosSummary.created ?? metrics.todos?.created ?? 0}
                        </p>
                        <p className="text-xs text-bone-dim mt-1">
                          {todosSummary.completed ??
                            metrics.todos?.completed ??
                            0}{" "}
                          completed
                        </p>
                      </div>
                    </div>
                  )}

                  {topTags.length > 0 && (
                    <div className="mt-4 flex flex-wrap gap-2">
                      {topTags.slice(0, 6).map((tag) => (
                        <span
                          key={tag.name}
                          className="px-3 py-1 rounded-full border border-gold/20 text-xs text-gold bg-gold/5"
                        >
                          {tag.name}
                        </span>
                      ))}
                    </div>
                  )}

                  {sessions.length > 0 && (
                    <div className="mt-6 space-y-3">
                      <p className="text-sm font-semibold text-bone">
                        Session Highlights
                      </p>
                      <ul className="space-y-2 text-sm text-bone-dim">
                        {sessions.slice(0, 4).map((session) => (
                          <li
                            key={session.id}
                            className="border border-gold/10 rounded-lg p-3 bg-black-soft/40"
                          >
                            <p className="text-bone font-medium">
                              Session {session.id}
                            </p>
                            {session.summary && (
                              <p className="mt-1 text-xs leading-relaxed">
                                {session.summary}
                              </p>
                            )}
                            <div className="mt-2 flex gap-3 text-xs">
                              <span>{session.todo_count ?? 0} tasks</span>
                              <span>{session.duration_minutes ?? 0} min</span>
                              <span className="capitalize">
                                {session.status}
                              </span>
                            </div>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {Array.isArray(todosSummary.highlights) &&
                    todosSummary.highlights.length > 0 && (
                      <div className="mt-6 space-y-2">
                        <p className="text-sm font-semibold text-bone">
                          Task Highlights
                        </p>
                        <ul className="space-y-2 text-sm text-bone-dim">
                          {todosSummary.highlights
                            .slice(0, 4)
                            .map((todo: any, idx: number) => (
                              <li
                                key={`${todo.title}-${idx}`}
                                className="border border-gold/10 rounded-lg p-3 bg-black-soft/30"
                              >
                                <p className="text-bone">{todo.title}</p>
                                <p className="text-xs capitalize mt-1">
                                  Status: {todo.status ?? "unknown"}
                                </p>
                              </li>
                            ))}
                        </ul>
                      </div>
                    )}

                  <div className="mt-4 text-xs text-bone-dim">
                    <div>
                      <span className="font-semibold text-bone">From:</span>{" "}
                      {formatDate(report.period_start, periodTimezone, false)}
                    </div>
                    <div>
                      <span className="font-semibold text-bone">To:</span>{" "}
                      {formatDate(report.period_end, periodTimezone, false)}
                    </div>
                    <div>
                      <span className="font-semibold text-bone">Timezone:</span>{" "}
                      {periodTimezone}
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
