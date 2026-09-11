import { Component, type ErrorInfo, type ReactNode } from "react";
import { Button } from "./ui";
export class ErrorBoundary extends Component<{ children: ReactNode; }, { failed: boolean; }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidCatch(error: Error, info: ErrorInfo) { console.error("Workspace rendering failed", error, info.componentStack); }
  render() {
    if (!this.state.failed) return this.props.children;
    return <div className="cf-page"><div className="cf-panel py-16 text-center"><h1 className="text-2xl font-semibold">This view could not load.</h1><p className="mt-3 mb-6 text-slate-500">Your saved records are unchanged. Reload to open the latest application.</p><Button onClick={() => window.location.reload()}>Reload workspace</Button></div></div>;
  }
}
