import { SignIn as ClerkSignIn } from "@clerk/clerk-react";
import { motion } from "framer-motion";
import Logo from "./Logo";

export default function SignIn() {
  return (
    <div className="min-h-screen bg-black flex items-center justify-center p-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md space-y-8"
      >
        {/* Logo and branding */}
        <div className="text-center space-y-4">
          <div className="flex justify-center">
            <Logo size="large" />
          </div>
          <div>
            <h1 className="text-3xl font-display font-bold bg-gradient-gold bg-clip-text text-transparent">
              Welcome to Speakly
            </h1>
            <p className="text-bone mt-2 text-base">
              Transform your voice recordings into actionable insights
            </p>
          </div>
        </div>

        {/* Clerk Sign In component with custom styling */}
        <div className="flex justify-center">
          <ClerkSignIn
            appearance={{
              elements: {
                rootBox: "w-full",
                card: "bg-gradient-to-br from-black-soft to-black border-2 border-gold/30 shadow-2xl",
                headerTitle: "text-bone font-display text-lg",
                headerSubtitle: "text-bone",
                socialButtonsBlockButton:
                  "border-2 border-gold/30 text-bone hover:bg-gold/10",
                socialButtonsBlockButtonText: "text-bone",
                socialButtonsBlockButtonArrow: "text-bone",
                socialButtonsProviderIcon: "brightness-0 invert",
                dividerLine: "bg-gold/30",
                dividerText: "text-bone",
                formButtonPrimary:
                  "bg-gradient-gold text-black font-semibold hover:shadow-lg hover:shadow-gold/50",
                formFieldLabel: "text-bone",
                formFieldInput:
                  "bg-black border-2 border-gold/20 text-bone focus:border-gold",
                formFieldInputShowPasswordButton: "text-bone",
                footerAction: "text-bone",
                footerActionText: "text-bone",
                footerActionLink: "text-gold hover:text-gold-bright",
                identityPreviewText: "text-bone",
                identityPreviewEditButton: "text-gold hover:text-gold-bright",
                otpCodeFieldInput: "bg-black border-2 border-gold/20 text-bone",
                formResendCodeLink: "text-gold hover:text-gold-bright",
              },
            }}
          />
        </div>

        {/* Features list */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="text-center space-y-3 pt-6"
        >
          <p className="text-sm text-bone uppercase tracking-wider font-semibold">
            Why Speakly?
          </p>
          <div className="grid grid-cols-1 gap-2 text-sm text-bone">
            <div className="flex items-center justify-center gap-2">
              <span className="text-gold text-base">✨</span>
              <span>AI-powered transcription & summaries</span>
            </div>
            <div className="flex items-center justify-center gap-2">
              <span className="text-green text-base">✓</span>
              <span>Automatic task extraction</span>
            </div>
            <div className="flex items-center justify-center gap-2">
              <span className="text-blue text-base">🔗</span>
              <span>TickTick integration</span>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </div>
  );
}
