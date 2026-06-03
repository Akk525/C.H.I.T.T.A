"use client";

import React from "react";
import Link from "next/link";

type State = { hasError: boolean; error: Error | null };

function ErrorFallback({ error }: { error: Error | null }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-b from-slate-50 to-white px-4">
      <div className="chitta-card max-w-md w-full rounded-2xl bg-white p-8 shadow-lg text-center">
        <div className="text-xs font-semibold tracking-[0.2em] text-emerald-700 mb-2">CHITTA</div>
        <h1 className="text-xl font-semibold text-slate-900 mb-2">Something went wrong</h1>
        <p className="text-sm text-slate-500 mb-6 leading-relaxed">
          An unexpected error occurred. You can try reloading the page or returning to the home screen.
        </p>
        {error?.message && (
          <div className="mb-6 rounded-lg bg-slate-50 border border-slate-100 px-3 py-2 text-left">
            <div className="text-[10px] font-semibold text-slate-400 mb-1">ERROR</div>
            <div className="text-xs font-mono text-slate-600 break-all">{error.message}</div>
          </div>
        )}
        <div className="flex flex-col gap-2">
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="rounded-xl bg-emerald-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-emerald-700 transition-colors"
          >
            Reload page
          </button>
          <Link
            href="/"
            className="rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
          >
            Back to Home
          </Link>
        </div>
      </div>
    </div>
  );
}

export class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  State
> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return <ErrorFallback error={this.state.error} />;
    }
    return this.props.children;
  }
}
