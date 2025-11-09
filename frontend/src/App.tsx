import { useState, useEffect, useRef } from "react";
import { useAuth, useUser, UserButton } from "@clerk/clerk-react";
import { motion } from "framer-motion";
import BulkUploader from "./components/BulkUploader";
import SessionsList from "./components/SessionsList";
import TickTickConnect from "./components/TickTickConnect";
import RecordingPreferences from "./components/RecordingPreferences";
import CommandPalette from "./components/CommandPalette";
import { ErrorBoundary } from "./components/ErrorBoundary";
import SignIn from "./components/SignIn";
import Logo from "./components/Logo";
import LoadingSpinner from "./components/LoadingSpinner";
import { Compass, FolderOpen } from "lucide-react";
import { fetchSessions, SessionRecord, setAuthTokenProvider } from "./api";
import { cn } from "@/lib/utils";
import JourneysView from "./components/JourneysView";

type Tab = "upload" | "journeys";

export default function App() {
  const { isLoaded, isSignedIn, getToken } = useAuth();
  const { user } = useUser();
  const [activeTab, setActiveTab] = useState<Tab>("upload");
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  const [sessions, setSessions] = useState<SessionRecord[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [targetSessionId, setTargetSessionId] = useState<number | null>(null);
  const [tokenReady, setTokenReady] = useState(false);
  const [pendingIntegrationScroll, setPendingIntegrationScroll] =
    useState(false);
  const integrationSectionRef = useRef<HTMLDivElement | null>(null);

  // Set auth token for API calls (ALL HOOKS MUST BE BEFORE CONDITIONAL RETURNS!)
  useEffect(() => {
    let isCurrent = true;
    if (isSignedIn) {
      setTokenReady(false);
      setAuthTokenProvider(() => getToken());
      getToken()
        .then(() => {
          if (isCurrent) {
            setTokenReady(true);
          }
        })
        .catch(() => {
          if (isCurrent) {
            setTokenReady(true); // allow UI to proceed and surface auth errors
          }
        });
    } else {
      setAuthTokenProvider(null);
      setTokenReady(false);
    }
    return () => {
      isCurrent = false;
    };
  }, [isSignedIn, getToken]);

  // Load sessions for command palette (only when token is ready)
  useEffect(() => {
    if (!isSignedIn || !tokenReady) return; // Skip if not signed in or token not ready

    const loadSessions = async () => {
      try {
        const data = await fetchSessions();
        setSessions(data);
      } catch (error) {
        // Failed to load sessions - will show empty state
      }
    };
    loadSessions();
  }, [refreshTrigger, isSignedIn, tokenReady]);

  // Keyboard shortcut for command palette
  useEffect(() => {
    if (!isSignedIn) return; // Skip if not signed in

    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setCommandPaletteOpen(true);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isSignedIn]);

  useEffect(() => {
    if (!pendingIntegrationScroll || activeTab !== "upload") return;

    const scrollTimeout = window.setTimeout(() => {
      integrationSectionRef.current?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
      setPendingIntegrationScroll(false);
    }, 200);

    return () => window.clearTimeout(scrollTimeout);
  }, [pendingIntegrationScroll, activeTab]);

  // Show loading or sign-in AFTER all hooks
  if (!isLoaded) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <LoadingSpinner message="Initializing Speakly..." size="large" />
      </div>
    );
  }

  if (!isSignedIn) {
    return <SignIn />;
  }

  // Show loading while setting up authentication token
  if (!tokenReady) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <LoadingSpinner message="Setting up your session..." size="large" />
      </div>
    );
  }

  const handleOpenIntegrations = () => {
    setActiveTab("upload");
    setPendingIntegrationScroll(true);
  };

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-black">
        {/* Header */}
        <motion.header
          initial={{ y: -20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          className="sticky top-0 z-50 backdrop-blur-xl bg-black/80 border-b border-gold/20"
        >
          <div className="max-w-7xl mx-auto px-4 py-4">
            <div className="flex items-center justify-between">
              {/* Logo Section */}
              <div className="flex items-center gap-4">
                <Logo size="medium" showText={true} />
                <motion.p
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.2 }}
                  className="text-sm text-bone-dim font-medium hidden md:block"
                >
                  Turn Conversations into Action
                </motion.p>
              </div>

              {/* Tab Navigation & User */}
              <div className="flex items-center gap-4">
                <nav className="flex gap-2 bg-black-soft/50 p-1 rounded-lg border border-gold/20">
                  <motion.button
                    onClick={() => setActiveTab("upload")}
                    className={cn(
                      "flex items-center gap-2 px-4 py-2 rounded-md font-medium text-sm transition-all",
                      activeTab === "upload"
                        ? "bg-gradient-blue text-bone shadow-lg shadow-blue/30"
                        : "text-bone-dim hover:text-bone hover:bg-black-soft",
                    )}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    aria-label="Upload Audio"
                  >
                    <FolderOpen size={18} />
                    <span>My Audio</span>
                  </motion.button>
                  <motion.button
                    onClick={() => setActiveTab("journeys")}
                    className={cn(
                      "flex items-center gap-2 px-4 py-2 rounded-md font-medium text-sm transition-all",
                      activeTab === "journeys"
                        ? "bg-gradient-blue text-bone shadow-lg shadow-blue/30"
                        : "text-bone-dim hover:text-bone hover:bg-black-soft",
                    )}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    aria-label="Journeys"
                  >
                    <Compass size={18} />
                    <span>Journeys</span>
                  </motion.button>
                </nav>

                {/* User Button */}
                <UserButton
                  afterSignOutUrl="/"
                  appearance={{
                    elements: {
                      avatarBox:
                        "w-10 h-10 border-2 border-gold/30 hover:border-gold",
                      userButtonPopoverCard:
                        "bg-gradient-to-br from-black-soft to-black border-2 border-gold/30",
                      userButtonPopoverActionButton:
                        "text-bone hover:bg-gold/10",
                      userButtonPopoverActionButtonText: "text-bone",
                      userButtonPopoverActionButtonIcon: "brightness-0 invert",
                      userButtonPopoverFooter: "hidden",
                      userPreviewMainIdentifier: "text-bone font-semibold",
                      userPreviewSecondaryIdentifier: "text-bone-dim",
                    },
                  }}
                />
              </div>
            </div>
          </div>
        </motion.header>

        {/* Main Content */}
        <main className="min-h-[calc(100vh-80px)]">
          {activeTab === "upload" && (
            <div className="w-full max-w-7xl mx-auto px-4 pt-6 space-y-6">
              <div className="grid gap-6 xl:grid-cols-[1.7fr_minmax(320px,1fr)] items-stretch">
                <BulkUploader
                  className="py-2 h-full"
                  onUploadComplete={() => setRefreshTrigger((prev) => prev + 1)}
                />
                <div className="flex flex-col gap-6 h-full">
                  <RecordingPreferences />
                  <div
                    ref={integrationSectionRef}
                    id="integrations"
                    className="flex-1 flex"
                  >
                    <TickTickConnect className="flex-1" />
                  </div>
                </div>
              </div>
              <SessionsList
                refreshTrigger={refreshTrigger}
                searchQuery={searchQuery}
                targetSessionId={targetSessionId}
                onSearchApplied={() => {
                  setSearchQuery("");
                  setTargetSessionId(null);
                }}
              />
            </div>
          )}
          {activeTab === "journeys" && <JourneysView />}
        </main>

        {/* Command Palette */}
        <CommandPalette
          isOpen={commandPaletteOpen}
          onClose={() => setCommandPaletteOpen(false)}
          sessions={sessions}
          onUpload={() => {
            setActiveTab("upload");
            // Just navigate to upload tab - user can click the upload area
          }}
          onNavigateToSession={(sessionId) => {
            setActiveTab("upload");
            setTargetSessionId(sessionId);
          }}
          onOpenIntegrations={handleOpenIntegrations}
          onSearch={(query) => {
            setActiveTab("upload");
            setSearchQuery(query);
          }}
        />
      </div>
    </ErrorBoundary>
  );
}
