import { Suspense } from "react";
import SiteExplorerPage from "@/components/SiteExplorerPage";

export default function DemoPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center text-sm text-slate-600">
          Loading demo…
        </div>
      }
    >
      <SiteExplorerPage />
    </Suspense>
  );
}
