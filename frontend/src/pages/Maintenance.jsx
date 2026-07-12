import { useEffect, useState, useCallback } from "react";
import api from "../api/api";
import { useAuth } from "../context/AuthProvider";
import { useToast } from "../components/Toast";

const PRIORITY_OPTIONS = ["low", "medium", "high", "critical"];

// Mirrors the backend's maintenance_state_machine — only these forward moves
// are ever valid from a given current status.
const NEXT_STATUS_OPTIONS = {
  pending: ["approved"],
  approved: ["technician_assigned"],
  technician_assigned: ["in_progress"],
  in_progress: ["resolved"],
  resolved: [],
};

function ReportIssueModal({ isOpen, onClose, onReported }) {
  const { showToast } = useToast();
  const [assets, setAssets] = useState([]);
  const [form, setForm] = useState({ asset_id: "", issue_description: "", priority: "medium" });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!isOpen) return;
    api
      .get("/assets", { params: { limit: 200 } })
      .then((res) => setAssets(res.data.items))
      .catch(() => setAssets([]));
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      await api.post("/maintenance", form);
      showToast("Issue reported.");
      onReported();
      onClose();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to report issue.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-md rounded-lg border border-gray-300 bg-white p-6">
        <h3 className="mb-4 text-lg font-semibold text-black">Report an Issue</h3>

        {error && (
          <div className="mb-4 rounded-md border border-black p-3 text-sm text-black">{error}</div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-600">Asset</label>
            <select
              required
              value={form.asset_id}
              onChange={(e) => setForm({ ...form, asset_id: e.target.value })}
              className="mt-1 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-black focus:border-black"
            >
              <option value="">Select an asset…</option>
              {assets.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.asset_tag} · {a.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600">Issue description</label>
            <textarea
              required
              rows={4}
              value={form.issue_description}
              onChange={(e) => setForm({ ...form, issue_description: e.target.value })}
              className="mt-1 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-black focus:border-black"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600">Priority</label>
            <select
              value={form.priority}
              onChange={(e) => setForm({ ...form, priority: e.target.value })}
              className="mt-1 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-black focus:border-black"
            >
              {PRIORITY_OPTIONS.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-black hover:bg-gray-100"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="rounded-md bg-black px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              {isSubmitting ? "Reporting…" : "Report Issue"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function Maintenance() {
  const { hasRole } = useAuth();
  const { showToast } = useToast();
  const canReview = hasRole("admin", "asset_manager");

  const [requests, setRequests] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const fetchRequests = useCallback(async () => {
    setIsLoading(true);
    try {
      const { data } = await api.get("/maintenance");
      setRequests(data.items);
    } catch {
      showToast("Failed to load maintenance requests.", "error");
    } finally {
      setIsLoading(false);
    }
  }, [showToast]);

  useEffect(() => {
    fetchRequests();
  }, [fetchRequests]);

  const handleStatusChange = async (requestId, newStatus) => {
    try {
      await api.patch(`/maintenance/${requestId}/status`, { status: newStatus });
      showToast("Request updated.");
      fetchRequests();
    } catch (err) {
      showToast(err.response?.data?.detail || "Update rejected.", "error");
    }
  };

  return (
    <div className="p-8">
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-2xl font-bold text-black">Maintenance</h2>
        <button
          onClick={() => setIsModalOpen(true)}
          className="rounded-md bg-black px-4 py-2 text-sm font-medium text-white hover:bg-gray-800"
        >
          + Report Issue
        </button>
      </div>

      <div className="overflow-x-auto rounded-lg border border-gray-300 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-gray-300 bg-gray-50">
            <tr>
              <th className="px-4 py-3 font-semibold text-black">Asset</th>
              <th className="px-4 py-3 font-semibold text-black">Issue</th>
              <th className="px-4 py-3 font-semibold text-black">Priority</th>
              <th className="px-4 py-3 font-semibold text-black">Reported By</th>
              <th className="px-4 py-3 font-semibold text-black">Status</th>
              {canReview && <th className="px-4 py-3 font-semibold text-black">Advance</th>}
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-gray-500">
                  Loading…
                </td>
              </tr>
            ) : requests.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-gray-500">
                  No maintenance requests yet.
                </td>
              </tr>
            ) : (
              requests.map((r) => {
                const nextOptions = NEXT_STATUS_OPTIONS[r.status] || [];
                return (
                  <tr key={r.id} className="border-b border-gray-200 last:border-0">
                    <td className="px-4 py-3 text-black">
                      {r.asset?.asset_tag} · {r.asset?.name}
                    </td>
                    <td className="px-4 py-3 max-w-xs truncate text-black" title={r.issue_description}>
                      {r.issue_description}
                    </td>
                    <td className="px-4 py-3">
                      <span className="rounded border border-black px-2 py-0.5 text-xs uppercase text-black">
                        {r.priority}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-600">{r.reported_by?.full_name || "—"}</td>
                    <td className="px-4 py-3">
                      <span className="rounded border border-black px-2 py-0.5 text-xs uppercase text-black">
                        {r.status.replace("_", " ")}
                      </span>
                    </td>
                    {canReview && (
                      <td className="px-4 py-3">
                        {nextOptions.length > 0 ? (
                          <select
                            defaultValue=""
                            onChange={(e) => {
                              if (e.target.value) handleStatusChange(r.id, e.target.value);
                              e.target.value = "";
                            }}
                            className="rounded-md border border-gray-300 bg-white px-2 py-1 text-xs text-black"
                          >
                            <option value="" disabled>
                              Set status…
                            </option>
                            {nextOptions.map((s) => (
                              <option key={s} value={s}>
                                {s.replace("_", " ")}
                              </option>
                            ))}
                          </select>
                        ) : (
                          <span className="text-xs text-gray-400">Final</span>
                        )}
                      </td>
                    )}
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      <ReportIssueModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onReported={fetchRequests}
      />
    </div>
  );
}
