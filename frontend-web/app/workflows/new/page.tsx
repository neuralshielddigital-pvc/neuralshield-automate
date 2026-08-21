"use client";

import { useEffect, useState } from "react";
import { apiRequest } from "@/lib/api";
import { getAccessToken } from "@/lib/token-storage";
import { useRouter } from "next/navigation";

type ActionType = "CREATE_LEAD" | "SEND_EMAIL" | "SEND_WEBHOOK" | "WAIT" | "CONDITION";

export default function NewWorkflowPage() {
  const router = useRouter();

  const [name, setName] = useState("");
  const [triggerType, setTriggerType] = useState("WEBHOOK_RECEIVED");
  const [actionType, setActionType] = useState<ActionType>("CREATE_LEAD");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const token = getAccessToken();
    if (!token) {
      router.replace("/login");
    }
  }, [router]);

  async function createWorkflow() {
    try {
      setLoading(true);

      const config =
        actionType === "SEND_WEBHOOK"
          ? { url: "https://api.neuralshielddigital.com/api/health" }
          : actionType === "SEND_EMAIL"
          ? { to: "admin-test@example.com", subject: "Workflow Test", body: "Test email from workflow builder" }
          : actionType === "WAIT"
          ? { seconds: 5 }
          : actionType === "CONDITION"
          ? {
              left: "{{email}}",
              operator: "contains",
              right: "@gmail.com",
              on_true: [
                {
                  type: "ADD_AUDIT_LOG",
                  config: { action: "condition_true_gmail" },
                },
              ],
              on_false: [
                {
                  type: "ADD_AUDIT_LOG",
                  config: { action: "condition_false_not_gmail" },
                },
              ],
            }
          : { email: "{{email}}", name: "{{name}}", phone: "{{phone}}" };

      await apiRequest("/api/workflows", {
        method: "POST",
        body: JSON.stringify({
          name,
          description: "Created from Workflow Builder UI",
          is_active: true,
          trigger: {
            type: triggerType,
            config: {},
          },
          actions: [
            {
              type: actionType,
              config,
            },
          ],
        }),
      });

      router.push("/admin/workflows");
    } catch (err) {
      console.error(err);
      alert(err instanceof Error ? err.message : "Failed to create workflow");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="dashboard-shell">
      <div className="mx-auto max-w-2xl px-4 py-8">
        <h1 className="text-3xl font-bold mb-6">Create Workflow</h1>

        <div className="space-y-4">
          <input
            className="w-full border p-3 rounded"
            placeholder="Workflow Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />

          <select
            className="w-full border p-3 rounded"
            value={triggerType}
            onChange={(e) => setTriggerType(e.target.value)}
          >
            <option value="WEBHOOK_RECEIVED">Webhook</option>
              <option value="SCHEDULED">Scheduled</option>
            <option value="NEW_LEAD">New Lead</option>
            <option value="CAMPAIGN_ACTIVATED">Campaign Activated</option>
          </select>

          <select
            className="w-full border p-3 rounded"
            value={actionType}
            onChange={(e) => setActionType(e.target.value as ActionType)}
          >
            <option value="CREATE_LEAD">Create Lead</option>
            <option value="SEND_EMAIL">Send Email</option>
            <option value="SEND_WEBHOOK">Send Webhook</option>
            <option value="WAIT">Wait 5 Seconds</option>
            <option value="CONDITION">Condition: Email contains @gmail.com</option>
          </select>

          <button
            onClick={createWorkflow}
            disabled={loading || !name.trim()}
            className="rounded bg-black text-white px-6 py-3 disabled:opacity-50"
          >
            {loading ? "Creating..." : "Create Workflow"}
          </button>
        </div>
      </div>
    </main>
  );
}
