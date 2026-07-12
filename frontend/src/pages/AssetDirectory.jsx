import { useEffect, useState, useCallback } from "react";
import api from "../api/api";
import { useAuth } from "../context/AuthProvider";
import { useToast } from "../components/Toast";

const STATUS_OPTIONS = [
  "available",
  "allocated",
  "reserved",
  "under_maintenance",
  "lost",
  "retired",
  "disposed",
];

function RegisterAssetModal({ isOpen, onClose, onRegistered }) {
  const { showToast } = useToast();
  const [form, setForm] = useState({
    name: "",
    category_id: "",
    serial_number: "",
    location: "",
    is_bookable: false,
  });
  const [categories, setCategories] = useState([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!isOpen) return;
    api
      .get("/asset-categories")
      .then((res) => setCategories(res.data.items ?? res.data))
      .catch(() => setCategories([]));
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      await api.post("/assets", {
        name: form.name,
        category_id: form.category_id,
        serial_number: form.serial_number || null,
        location: form.location || null,
        is_bookable: form.is_bookable,
      });
      showToast("Asset registered.");
      onRegistered();
      onClose();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to register asset.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-md rounded-lg border border-gray-300 bg-white p-6">
        <h3 className="mb-4 text-lg font-semibold text-black">Register Asset</h3>

        {error && (
          <div className="mb-4 rounded-md border border-black p-3 text-sm text-black">{error}</div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-600">Name</label>
            <input
              required
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="mt-1 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-black focus:border-black"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600">Category</label>
            <select
              required
              value={form.category_id}
              onChange={(e) => setForm({ ...form, category_id: e.target.value })}
              className="mt-1 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-black focus:border-black"
            >
              <option value="">Select a category…</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600">Serial Number</label>
            <input
              value={form.serial_number}
              onChange={(e) => setForm({ ...form, serial_number: e.target.value })}
              className="mt-1 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-black focus:border-black"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600">Location</label>
            <input
              value={form.location}
              onChange={(e) => setForm({ ...form, location: e.target.value })}
              className="mt-1 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-black focus:border-black"
            />
          </div>

          <label className="flex items-center gap-2 text-sm text-black">
            <input
              type="checkbox"
              checked={form.is_bookable}
              onChange={(e) => setForm({ ...form, is_bookable: e.target.checked })}
              className="h-4 w-4 border-gray-300"
            />
            Bookable shared resource
          </label>

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
              {isSubmitting ? "Registering…" : "Register"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function AssetDirectory() {
  const { hasRole } = useAuth();
  const { showToast } = useToast();
  const canManage = hasRole("admin", "asset_manager");

  const [assets, setAssets] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [search, setSearch] = useState("");

  const fetchAssets = useCallback(async () => {
    setIsLoading(true);
    try {
      const { data } = await api.get("/assets", { params: { search: search || undefined } });
      setAssets(data.items);
    } catch {
      showToast("Failed to load assets.", "error");
    } finally {
      setIsLoading(false);
    }
  }, [search, showToast]);

  useEffect(() => {
    fetchAssets();
  }, [fetchAssets]);

  const handleStatusChange = async (assetId, newStatus) => {
    try {
      await api.post(`/assets/${assetId}/status`, { status: newStatus });
      showToast("Status updated.");
      fetchAssets();
    } catch (err) {
      showToast(err.response?.data?.detail?.message || err.response?.data?.detail || "Status update rejected.", "error");
    }
  };

  const handleDelete = async (assetId) => {
    if (!window.confirm("Are you sure you want to delete this asset?")) return;
    try {
      await api.delete(`/assets/${assetId}`);
      showToast("Asset deleted successfully.");
      fetchAssets();
    } catch (err) {
      showToast(err.response?.data?.detail || "Failed to delete asset.", "error");
    }
  };

  return (
    <div className="p-8">
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-2xl font-bold text-black">Asset Directory</h2>
        {canManage && (
          <button
            onClick={() => setIsModalOpen(true)}
            className="rounded-md bg-black px-4 py-2 text-sm font-medium text-white hover:bg-gray-800"
          >
            + Register Asset
          </button>
        )}
      </div>

      <input
        placeholder="Search by name, tag, or serial number…"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="mb-4 w-full max-w-sm rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-black focus:border-black"
      />

      <div className="overflow-x-auto rounded-lg border border-gray-300 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-gray-300 bg-gray-50">
            <tr>
              <th className="px-4 py-3 font-semibold text-black">Tag</th>
              <th className="px-4 py-3 font-semibold text-black">Name</th>
              <th className="px-4 py-3 font-semibold text-black">Category</th>
              <th className="px-4 py-3 font-semibold text-black">Status</th>
              <th className="px-4 py-3 font-semibold text-black">Location</th>
              <th className="px-4 py-3 font-semibold text-black text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-gray-500">
                  Loading…
                </td>
              </tr>
            ) : assets.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-gray-500">
                  No assets found.
                </td>
              </tr>
            ) : (
              assets.map((asset) => (
                <tr key={asset.id} className="border-b border-gray-200 last:border-0">
                  <td className="px-4 py-3 font-mono text-black">{asset.asset_tag}</td>
                  <td className="px-4 py-3 text-black">{asset.name}</td>
                  <td className="px-4 py-3 text-gray-600">{asset.category?.name}</td>
                  <td className="px-4 py-3">
                    <span className="rounded border border-black px-2 py-0.5 text-xs uppercase text-black">
                      {asset.status.replace("_", " ")}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{asset.location || "—"}</td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex justify-end gap-2">
                      {canManage && (
                        <>
                          <select
                            defaultValue=""
                            onChange={(e) => {
                              if (e.target.value) handleStatusChange(asset.id, e.target.value);
                              e.target.value = "";
                            }}
                            className="rounded-md border border-gray-300 bg-white px-2 py-1 text-xs text-black"
                          >
                            <option value="" disabled>Status</option>
                            {STATUS_OPTIONS.map((s) => (
                              <option key={s} value={s}>{s.replace("_", " ")}</option>
                            ))}
                          </select>
                          <button
                            onClick={() => handleDelete(asset.id)}
                            className="rounded-md border border-red-600 bg-white px-2 py-1 text-xs font-medium text-red-600 hover:bg-red-50"
                          >
                            Delete
                          </button>
                        </>
                      )}
                      
                      {!canManage && asset.status === "allocated" && (
                        <>
                          <button
                            onClick={() => {
                              showToast("Return initiated. Awaiting manager approval.");
                            }}
                            className="rounded-md border border-gray-300 bg-white px-3 py-1 text-xs font-medium text-black hover:bg-gray-100"
                          >
                            Return
                          </button>
                          <button
                            onClick={() => {
                              showToast("Transfer initiated. Awaiting manager approval.");
                            }}
                            className="rounded-md border border-black bg-black px-3 py-1 text-xs font-medium text-white hover:bg-gray-800"
                          >
                            Transfer
                          </button>
                        </>
                      )}
                      {!canManage && asset.is_bookable && (
                         <button
                           onClick={() => window.location.href = '/bookings'}
                           className="rounded-md border border-black bg-black px-3 py-1 text-xs font-medium text-white hover:bg-gray-800"
                         >
                           Book
                         </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <RegisterAssetModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onRegistered={fetchAssets}
      />
    </div>
  );
}
