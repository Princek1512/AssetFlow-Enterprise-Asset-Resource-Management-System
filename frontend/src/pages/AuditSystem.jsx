import { useEffect, useState, useCallback, useMemo } from "react";
import api from "../api/api";
import { useToast } from "../components/Toast";
import { Search, AlertTriangle, ShieldCheck, XCircle } from "lucide-react";

export default function AuditSystem() {
  const { showToast } = useToast();
  const [cycles, setCycles] = useState([]);
  const [activeCycle, setActiveCycle] = useState(null);
  
  const [assets, setAssets] = useState([]);
  const [categories, setCategories] = useState([]);
  const [records, setRecords] = useState([]);
  
  const [selectedCategory, setSelectedCategory] = useState("all");
  // Department filter included for mockup compliance, though assets might not have department_id natively
  const [selectedDepartment, setSelectedDepartment] = useState("all");
  
  const [newCycleName, setNewCycleName] = useState("");
  const [newCycleDesc, setNewCycleDesc] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  const fetchCyclesAndCategories = useCallback(async () => {
    setIsLoading(true);
    try {
      const [cyclesRes, catRes] = await Promise.all([
        api.get("/audit/cycles"),
        api.get("/asset-categories")
      ]);
      setCycles(cyclesRes.data);
      setCategories(catRes.data.items || []);
      if (cyclesRes.data.length > 0 && !activeCycle) {
        setActiveCycle(cyclesRes.data[0]);
      }
    } catch {
      showToast("Failed to load audit cycles.", "error");
    } finally {
      setIsLoading(false);
    }
  }, [activeCycle, showToast]);

  const fetchCycleData = useCallback(async () => {
    if (!activeCycle) return;
    try {
      const [assetsRes, recordsRes] = await Promise.all([
        api.get("/assets", { params: { limit: 1000 } }),
        api.get(`/audit/cycles/${activeCycle.id}/records`)
      ]);
      setAssets(assetsRes.data.items || []);
      setRecords(recordsRes.data || []);
    } catch {
      showToast("Failed to load cycle details.", "error");
    }
  }, [activeCycle, showToast]);

  useEffect(() => {
    fetchCyclesAndCategories();
  }, [fetchCyclesAndCategories]);

  useEffect(() => {
    fetchCycleData();
  }, [fetchCycleData]);

  const handleCreateCycle = async (e) => {
    e.preventDefault();
    if (!newCycleName.trim()) return;
    try {
      const { data } = await api.post("/audit/cycles", {
        name: newCycleName,
        description: newCycleDesc,
      });
      showToast("Audit cycle created.");
      setNewCycleName("");
      setNewCycleDesc("");
      setActiveCycle(data);
      fetchCyclesAndCategories();
    } catch (err) {
      showToast(err.response?.data?.detail || "Failed to create cycle.", "error");
    }
  };

  const handleCompleteCycle = async () => {
    if (!activeCycle) return;
    try {
      const { data } = await api.post(`/audit/cycles/${activeCycle.id}/complete`, {});
      showToast("Audit cycle completed.");
      setActiveCycle(data);
      fetchCyclesAndCategories();
    } catch (err) {
      showToast(err.response?.data?.detail || "Failed to complete cycle.", "error");
    }
  };

  const handleAuditAsset = async (assetId, status) => {
    if (!activeCycle || activeCycle.is_completed) return;
    try {
      await api.post(`/audit/cycles/${activeCycle.id}/records`, {
        asset_id: assetId,
        status,
        notes: `Audited on ${new Date().toLocaleDateString()}`,
      });
      fetchCycleData();
    } catch (err) {
      showToast(err.response?.data?.detail || "Failed to submit audit.", "error");
    }
  };

  const getAssetAuditStatus = (assetId) => {
    const record = records.find((r) => r.asset_id === assetId);
    return record ? record.status : null; // null means unaudited
  };

  const filteredAssets = useMemo(() => {
    let result = assets;
    if (selectedCategory !== "all") {
      result = result.filter(a => a.category_id === selectedCategory);
    }
    return result;
  }, [assets, selectedCategory]);

  const missingAssets = useMemo(() => records.filter(r => r.status === "missing"), [records]);
  const damagedAssets = useMemo(() => records.filter(r => r.status === "damaged"), [records]);

  return (
    <div className="flex h-full flex-col bg-gray-50">
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar: Audit Cycles */}
        <div className="w-80 border-r border-gray-300 bg-white p-6 overflow-y-auto">
          <h2 className="mb-6 text-xl font-bold text-black">Audit System</h2>
          
          <div className="mb-8">
            <h3 className="mb-3 text-sm font-semibold text-black">New Cycle</h3>
            <form onSubmit={handleCreateCycle} className="space-y-3">
              <input
                required
                placeholder="Cycle Name"
                value={newCycleName}
                onChange={(e) => setNewCycleName(e.target.value)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-black focus:outline-none focus:ring-1 focus:ring-black"
              />
              <button
                type="submit"
                className="w-full rounded-md bg-black py-2 text-sm font-medium text-white hover:bg-gray-800"
              >
                Create Cycle
              </button>
            </form>
          </div>

          <div>
            <h3 className="mb-3 text-sm font-semibold text-black">Previous Cycles</h3>
            {isLoading ? (
              <p className="text-sm text-gray-500">Loading...</p>
            ) : (
              <div className="space-y-2">
                {cycles.map((c) => (
                  <button
                    key={c.id}
                    onClick={() => setActiveCycle(c)}
                    className={`w-full text-left rounded-md border p-3 transition-colors ${
                      activeCycle?.id === c.id
                        ? "border-black bg-gray-50 ring-1 ring-black"
                        : "border-gray-200 hover:border-gray-300"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-sm text-black truncate">{c.name}</span>
                      <span className={`text-[10px] uppercase font-bold tracking-wider ${c.is_completed ? 'text-gray-500' : 'text-green-600'}`}>
                        {c.is_completed ? "Closed" : "Active"}
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 overflow-y-auto p-8">
          {activeCycle ? (
            <div className="mx-auto max-w-5xl space-y-6">
              
              {/* Header Banner */}
              <div className="rounded-lg border border-gray-300 bg-white p-6 shadow-sm flex justify-between items-center">
                <div>
                  <h3 className="text-2xl font-bold text-black">{activeCycle.name}</h3>
                  <p className="text-sm text-gray-500 mt-1">
                    {new Date(activeCycle.created_at).toLocaleDateString()} — {activeCycle.description || "General Audit"}
                  </p>
                </div>
                {!activeCycle.is_completed && (
                  <button
                    onClick={handleCompleteCycle}
                    className="rounded-md border border-black px-4 py-2 text-sm font-medium text-black hover:bg-gray-100 transition-colors"
                  >
                    Close audit cycle
                  </button>
                )}
              </div>

              {/* Discrepancy Banner */}
              {(missingAssets.length > 0 || damagedAssets.length > 0) && (
                <div className="rounded-md border-l-4 border-l-red-600 bg-red-50 p-4 shadow-sm flex items-start gap-3">
                  <AlertTriangle className="h-5 w-5 text-red-600 mt-0.5" />
                  <div>
                    <h4 className="text-sm font-bold text-red-900">Discrepancy Detected</h4>
                    <p className="text-sm text-red-700 mt-1">
                      {missingAssets.length} assets missing, {damagedAssets.length} assets damaged.
                      Please review the logs before closing this cycle.
                    </p>
                  </div>
                </div>
              )}

              {/* Filters */}
              <div className="flex items-center gap-4 py-2">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-700">Category:</span>
                  <select
                    value={selectedCategory}
                    onChange={(e) => setSelectedCategory(e.target.value)}
                    className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-black focus:border-black focus:outline-none"
                  >
                    <option value="all">All Categories</option>
                    {categories.map(c => (
                      <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                  </select>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-700">Department:</span>
                  <select
                    value={selectedDepartment}
                    onChange={(e) => setSelectedDepartment(e.target.value)}
                    className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-black focus:border-black focus:outline-none"
                  >
                    <option value="all">All Departments</option>
                    {/* Hardcoded for visual mockup compliance if no departments from backend */}
                    <option value="engineering">Engineering</option>
                    <option value="design">Design</option>
                    <option value="hr">HR</option>
                  </select>
                </div>
              </div>

              {/* Asset List */}
              <div className="overflow-hidden rounded-lg border border-gray-300 bg-white shadow-sm">
                <table className="w-full text-left text-sm">
                  <thead className="border-b border-gray-300 bg-gray-50">
                    <tr>
                      <th className="px-6 py-4 font-semibold text-black">Asset Tag</th>
                      <th className="px-6 py-4 font-semibold text-black">Asset Name</th>
                      <th className="px-6 py-4 font-semibold text-black text-right">Audit Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {filteredAssets.length === 0 ? (
                      <tr>
                        <td colSpan={3} className="px-6 py-8 text-center text-gray-500">
                          No assets found.
                        </td>
                      </tr>
                    ) : (
                      filteredAssets.map(asset => {
                        const status = getAssetAuditStatus(asset.id);
                        return (
                          <tr key={asset.id} className="hover:bg-gray-50 transition-colors">
                            <td className="px-6 py-4 font-mono text-gray-600">{asset.asset_tag}</td>
                            <td className="px-6 py-4 font-medium text-black">{asset.name}</td>
                            <td className="px-6 py-4 text-right">
                              <div className="flex items-center justify-end gap-2">
                                {/* Verified Pill */}
                                <button
                                  onClick={() => handleAuditAsset(asset.id, "verified")}
                                  disabled={activeCycle.is_completed}
                                  className={`flex items-center gap-1 rounded-full border px-3 py-1 text-xs font-semibold transition-all ${
                                    status === "verified"
                                      ? "border-green-600 bg-green-50 text-green-700"
                                      : "border-gray-200 text-gray-400 hover:border-gray-300"
                                  }`}
                                >
                                  {status === "verified" && <ShieldCheck className="h-3 w-3" />}
                                  Verified
                                </button>

                                {/* Missing Pill */}
                                <button
                                  onClick={() => handleAuditAsset(asset.id, "missing")}
                                  disabled={activeCycle.is_completed}
                                  className={`flex items-center gap-1 rounded-full border px-3 py-1 text-xs font-semibold transition-all ${
                                    status === "missing"
                                      ? "border-red-600 bg-red-50 text-red-700"
                                      : "border-gray-200 text-gray-400 hover:border-gray-300"
                                  }`}
                                >
                                  {status === "missing" && <XCircle className="h-3 w-3" />}
                                  Missing
                                </button>

                                {/* Damaged Pill */}
                                <button
                                  onClick={() => handleAuditAsset(asset.id, "damaged")}
                                  disabled={activeCycle.is_completed}
                                  className={`flex items-center gap-1 rounded-full border px-3 py-1 text-xs font-semibold transition-all ${
                                    status === "damaged"
                                      ? "border-gray-600 bg-gray-100 text-gray-800"
                                      : "border-gray-200 text-gray-400 hover:border-gray-300"
                                  }`}
                                >
                                  {status === "damaged" && <AlertTriangle className="h-3 w-3" />}
                                  Damaged
                                </button>
                              </div>
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>

            </div>
          ) : (
            <div className="flex h-full items-center justify-center">
              <div className="text-center text-gray-500">
                <ShieldCheck className="mx-auto h-12 w-12 text-gray-300 mb-4" />
                <p>Select or create an audit cycle to begin.</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
