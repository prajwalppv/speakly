import { Component, ErrorInfo, ReactNode } from "react";
import { AlertTriangle, RefreshCw, RotateCw } from "lucide-react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

/**
 * Error Boundary component to catch and handle React errors gracefully.
 *
 * @example
 * <ErrorBoundary>
 *   <MyComponent />
 * </ErrorBoundary>
 */
export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("ErrorBoundary caught an error:", error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="min-h-screen bg-black flex items-center justify-center p-6">
          <div className="max-w-md w-full bg-gradient-to-br from-black-soft to-black border-2 border-red-500/30 rounded-xl p-8 text-center space-y-6">
            <div className="flex justify-center">
              <div className="w-16 h-16 rounded-full bg-red-500/20 border-2 border-red-500 flex items-center justify-center">
                <AlertTriangle className="text-red-500" size={32} />
              </div>
            </div>
            <h2 className="text-2xl font-display font-bold text-bone">
              Something went wrong
            </h2>
            <p className="text-bone-dim text-sm">
              {this.state.error?.message || "An unexpected error occurred"}
            </p>
            <div className="flex flex-col gap-3">
              <button
                className="w-full px-4 py-2 bg-gradient-blue text-bone rounded-lg font-medium hover:shadow-lg hover:shadow-blue/50 transition-all flex items-center justify-center gap-2"
                onClick={this.handleReset}
              >
                <RefreshCw size={18} />
                Try Again
              </button>
              <button
                className="w-full px-4 py-2 border-2 border-bone-dim text-bone-dim rounded-lg font-medium hover:bg-white/5 transition-all flex items-center justify-center gap-2"
                onClick={() => window.location.reload()}
              >
                <RotateCw size={18} />
                Reload Page
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
