"use client";

import { useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";
import { useRouter } from "next/navigation";

export default function EditWorkflowPage({
  params,
}: {
  params: { id: string };
}) {
  const router = useRouter();

  const [name, setName] = useState("");
  const [scheduleEnabled, setScheduleEnabled] = useState(false);
  const [scheduleCron, setScheduleCron] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function loadWorkflow() {
      try {
        const data = await apiRequest<{
          name: string;
          schedule_enabled?: boolean;
          schedule_cron?: string;
        }>(`/api/workflows/${params.id}`);

        setName(data.name);
        setScheduleEnabled(data.schedule_enabled ?? false);
        setScheduleCron(data.schedule_cron ?? "");
      } catch (err) {
        console.error(err);
      }
    }

    loadWorkflow();
  }, [params.id]);

  async function saveWorkflow() {
    try {
      setLoading(true);

      await apiRequest(`/api/workflows/${params.id}`, {
        method: "PUT",
        body: JSON.stringify({
          name,
        }),
      });

      await apiRequest(`/api/admin/workflows/${params.id}/schedule`, {
        method: "PATCH",
        body: JSON.stringify({
          schedule_enabled: scheduleEnabled,
          schedule_cron: scheduleEnabled ? scheduleCron : null,
          next_run_at: null,
        }),
      });

      router.push("/admin/workflows");
    } catch (err) {
      console.error(err);
      alert("Failed to update workflow");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="dashboard-shell">
      <div className="mx-auto max-w-2xl px-4 py-8">
        <h1 className="text-3xl font-bold mb-6">Edit Workflow</h1>

        <div className="space-y-4">
          <input
            className="w-full border p-3 rounded"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />

          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              checked={scheduleEnabled}
              onChange={(e) => setScheduleEnabled(e.target.checked)}
            />
            <label>Enable Schedule</label>
          </div>

          {scheduleEnabled && (
            <input
              className="w-full border p-3 rounded"
              placeholder="Cron (example: 0 */6 * * *)"
              value={scheduleCron}
              onChange={(e) => setScheduleCron(e.target.value)}
            />
          )}

          <button
            onClick={saveWorkflow}
            disabled={loading}
            className="rounded bg-black text-white px-6 py-3"
          >
            {loading ? "Saving..." : "Save Workflow"}
          </button>
        </div>
      </div>
    </main>
  );
}
