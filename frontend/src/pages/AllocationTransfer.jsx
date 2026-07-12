import { useEffect, useState, useCallback } from "react";
import api from "../api/api";
import { useToast } from "../components/Toast";
import { useAuth } from "../context/AuthProvider";
import { AlertCircle, History, ArrowRight } from "lucide-react";

export default function AllocationTransfer() {
  const { showToast } = useToast();
  const { hasRole, user } = useAuth();
  
  const [assets, setAssets] = useState([]);
  const [users, setUsers] = useState([]);
  const [transfers, setTransfers] = useState([]);
  
  const [selectedAssetId, setSelectedAssetId] = useState("");
  const [form, setForm] = useState({ to_user_id: "", reason: "" });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const isManager = hasRole("admin", "asset_manager", "department_head");

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    try {
      const promises = [api.get("/assets")];
      // Only managers can access these endpoints
      if (isManager) {
        promises.push(api.get("/admin/users"));
        promises.push(api.get("/transfer-requests"));
      }
      const results = await Promise.all(promises);
      
      setAssets(results[0].data.items || []);
      if (isManager) {
        const usersData = results[1].data;
        setUsers(Array.isArray(usersData) ? usersData : (usersData.items || []));
        setTransfers(results[2].data || []);
      }
      
      if (results[0].data.items?.length > 0 && !selectedAssetId) {
        setSelectedAssetId(results[0].data.items[0].id);
      }
    } catch (err) {
      showToast("Failed to load data.", "error");
    } finally {
      setIsLoading(false);
    }
  }, [showToast, selectedAssetId, isManager]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const selectedAsset = assets.find(a => a.id === selectedAssetId);
  const isAllocated = selectedAsset?.current_holder_id != null;
  const currentHolder = users.find(u => u.id === selectedAsset?.current_holder_id);

  const assetTransfers = transfers.filter(t => t.asset_id === selectedAssetId);
  const pendingTransfers = transfers.filter(t => t.status === "requested");

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedAsset) return;
    setIsSubmitting(true);
    
    try {
      if (isAllocated) {
        await api.post(`/assets/${selectedAsset.id}/transfer-requests`, {
          reason: form.reason
        });
        showToast("Transfer requested successfully.");
      } else {
        await api.post(`/assets/${selectedAsset.id}/allocate`, {
          employee_id: form.to_user_id
        });
        showToast("Asset allocated successfully.");
      }
      setForm({ to_user_id: "", reason: "" });
      fetchData();
    } catch (err) {
      const detail = err.response?.data?.detail;
      const message = typeof detail === "string" ? detail : detail?.message || "Could not complete action.";
      showToast(message, "error");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleAction = async (id, action) => {
    try {
      await api.post(`/transfer-requests/${id}/${action}`, { reason: "Manager decision" });
      showToast(`Transfer request ${action}d successfully.`);
      if (action === "approve") {
        await api.post(`/transfer-requests/${id}/reallocate`);
        showToast("Asset re-allocated to requester.");
      }
      fetchData();
    } catch (err) {
      showToast(err.response?.data?.detail || `Could not ${action} transfer.`, "error");
    }
  };

  return (
    <div className="p-8 max-w-5xl">
      <h2 className="mb-6 text-2xl font-bold text-black">Allocation & Transfer</h2>

      {isLoading ? (
        <p className="text-sm text-gray-500">Loading...</p>
      ) : (
        <>
          {/* ── Pending Transfer Requests (managers only) ── */}
          {isManager && pendingTransfers.length > 0 && (
            <div className="mb-8">
              <h3 className="mb-4 text-lg font-semibold text-black flex items-center gap-2">
                <AlertCircle className="h-5 w-5 text-orange-500" />
                Pending Transfer Requests ({pendingTransfers.length})
              </h3>
              <div className="overflow-x-auto rounded-lg border border-orange-200 bg-white">
                <table className="w-full text-left text-sm">
                  <thead className="border-b border-orange-200 bg-orange-50">
                    <tr>
                      <th className="px-4 py-3 font-semibold text-black">Asset</th>
                      <th className="px-4 py-3 font-semibold text-black">Requested By</th>
                      <th className="px-4 py-3 font-semibold text-black">Current Holder</th>
                      <th className="px-4 py-3 font-semibold text-black">Reason</th>
                      <th className="px-4 py-3 font-semibold text-black">Date</th>
                      <th className="px-4 py-3 font-semibold text-black text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pendingTransfers.map(t => (
                      <tr key={t.id} className="border-b border-gray-200 last:border-0">
                        <td className="px-4 py-3 text-black font-medium">
                          {t.asset?.name || "—"} <span className="text-xs text-gray-500 font-mono">({t.asset?.asset_tag})</span>
                        </td>
                        <td className="px-4 py-3 text-black">{t.requested_by?.full_name || "—"}</td>
                        <td className="px-4 py-3 text-gray-600">{t.current_holder?.full_name || "Unallocated"}</td>
                        <td className="px-4 py-3 text-gray-600 max-w-xs truncate" title={t.reason}>{t.reason || "—"}</td>
                        <td className="px-4 py-3 text-gray-500 text-xs">{new Date(t.created_at).toLocaleString()}</td>
                        <td className="px-4 py-3 text-right">
                          <div className="flex justify-end gap-2">
                            <button
                              onClick={() => handleAction(t.id, "approve")}
                              className="rounded-md border border-black bg-black px-3 py-1 text-xs font-medium text-white hover:bg-gray-800"
                            >
                              Approve
                            </button>
                            <button
                              onClick={() => handleAction(t.id, "reject")}
                              className="rounded-md border border-gray-300 bg-white px-3 py-1 text-xs font-medium text-black hover:bg-gray-100"
                            >
                              Reject
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* ── Allocate / Transfer Form + History ── */}
          <div className="grid grid-cols-1 gap-8 md:grid-cols-2">
            
            {/* Transfer Form Section */}
            <div>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700">Select Asset</label>
                <select
                  value={selectedAssetId}
                  onChange={(e) => setSelectedAssetId(e.target.value)}
                  className="mt-1 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-black focus:border-black focus:outline-none focus:ring-1 focus:ring-black"
                >
                  {assets.map(a => (
                    <option key={a.id} value={a.id}>{a.name} ({a.asset_tag})</option>
                  ))}
                </select>
              </div>

              {isAllocated && (
                <div className="mb-6 flex items-start gap-3 rounded-md border border-red-200 bg-red-50 p-4">
                  <AlertCircle className="h-5 w-5 text-red-600 mt-0.5" />
                  <div>
                    <h4 className="text-sm font-semibold text-red-800">Double-allocation Warning</h4>
                    <p className="text-sm text-red-600">
                      This asset is currently allocated to {currentHolder?.full_name || "someone"}. Proceeding will create a transfer request.
                    </p>
                  </div>
                </div>
              )}

              <div className="rounded-lg border border-gray-300 bg-white p-6">
                <h3 className="mb-4 text-lg font-semibold text-black">
                  {isAllocated ? "Request Transfer" : "Allocate Asset"}
                </h3>
                
                <form onSubmit={handleSubmit} className="space-y-4">
                  {isAllocated && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700">From</label>
                      <input
                        type="text"
                        disabled
                        value={currentHolder ? currentHolder.full_name : "Unallocated"}
                        className="mt-1 w-full rounded-md border border-gray-300 bg-gray-50 px-3 py-2 text-sm text-gray-600"
                      />
                    </div>
                  )}
                  
                  {!isAllocated && isManager && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700">To</label>
                      <select
                        required
                        value={form.to_user_id}
                        onChange={(e) => setForm({ ...form, to_user_id: e.target.value })}
                        className="mt-1 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-black focus:border-black focus:outline-none focus:ring-1 focus:ring-black"
                      >
                        <option value="" disabled>Select Employee</option>
                        {users
                          .filter(u => u.role === "employee")
                          .filter(u => {
                            // Department Heads can only allocate within their department
                            if (user?.role === "department_head") {
                              return u.department_id === user.department_id;
                            }
                            return true; // Admin/Asset Manager can allocate to anyone
                          })
                          .map(u => (
                            <option key={u.id} value={u.id}>{u.full_name}</option>
                          ))
                        }
                      </select>
                      {user?.role === "department_head" && (
                        <p className="mt-1 text-xs text-gray-500">Only employees in your department are shown.</p>
                      )}
                    </div>
                  )}

                  <div>
                    <label className="block text-sm font-medium text-gray-700">Reason</label>
                    <textarea
                      required
                      rows={3}
                      value={form.reason}
                      onChange={(e) => setForm({ ...form, reason: e.target.value })}
                      className="mt-1 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-black focus:border-black focus:outline-none focus:ring-1 focus:ring-black"
                    />
                  </div>
                  
                  <button
                    type="submit"
                    disabled={isSubmitting || !selectedAsset}
                    className="w-full rounded-md bg-black px-4 py-2 text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-50"
                  >
                    {isSubmitting ? "Submitting..." : (isAllocated ? "Submit Transfer Request" : "Allocate Asset")}
                  </button>
                </form>
              </div>
            </div>

            {/* Allocation History Section */}
            <div>
              <h3 className="mb-4 flex items-center gap-2 text-lg font-semibold text-black">
                <History className="h-5 w-5" /> Allocation History
              </h3>
              
              <div className="relative border-l-2 border-gray-200 ml-3 pl-6 space-y-6">
                {assetTransfers.length === 0 ? (
                  <p className="text-sm text-gray-500">No transfer history for this asset.</p>
                ) : (
                  assetTransfers.map((t) => (
                    <div key={t.id} className="relative">
                      <div className="absolute -left-[31px] top-1 h-3 w-3 rounded-full border-2 border-black bg-white"></div>
                      <div className="text-sm">
                        <p className="font-semibold text-black">
                          {t.status === "re_allocated" ? "Re-allocated" : t.status === "approved" ? "Approved" : t.status === "rejected" ? "Rejected" : "Requested"} by {t.requested_by?.full_name}
                        </p>
                        <p className="text-xs text-gray-500 mt-1">
                          {new Date(t.created_at).toLocaleDateString()}
                        </p>
                        {t.reason && (
                          <p className="mt-2 text-sm text-gray-600 bg-gray-50 p-2 rounded border border-gray-200">
                            "{t.reason}"
                          </p>
                        )}
                        <span className={`mt-2 inline-block text-xs border px-2 py-0.5 rounded uppercase ${
                          t.status === "requested" ? "border-orange-300 text-orange-700 bg-orange-50" :
                          t.status === "approved" || t.status === "re_allocated" ? "border-green-300 text-green-700 bg-green-50" :
                          "border-red-300 text-red-700 bg-red-50"
                        }`}>
                          {t.status.replace("_", " ")}
                        </span>
                        
                        {t.status === "requested" && isManager && (
                          <div className="mt-2 flex gap-2">
                            <button
                              onClick={() => handleAction(t.id, "approve")}
                              className="text-xs border border-black bg-black text-white px-2 py-0.5 rounded uppercase hover:bg-gray-800"
                            >
                              Approve
                            </button>
                            <button
                              onClick={() => handleAction(t.id, "reject")}
                              className="text-xs border border-gray-300 px-2 py-0.5 rounded text-black uppercase hover:bg-gray-100"
                            >
                              Reject
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
            
          </div>
        </>
      )}
    </div>
  );
}
