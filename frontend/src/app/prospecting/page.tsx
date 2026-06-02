import { Suspense } from "react";
import ProspectingPage from "@/components/ProspectingPage";

export default function Page() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center text-sm text-slate-600">
          Loading prospecting tool…
        </div>
      }
    >
      <ProspectingPage />
    </Suspense>
  );
}
