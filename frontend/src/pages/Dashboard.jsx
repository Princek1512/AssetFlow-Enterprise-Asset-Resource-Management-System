import { useEffect, useState, useCallback } from "react";
import api from "../api/api";

function KpiCard({ label, value, isLoading }) {
  return (
    <div className="rounded-lg border border-gray-300 bg-white p-6">
      <p className="text-xs font-medium uppercase tracking-wide text-gray-500">{label}</p>
      <p className="mt-2 text-3xl font-bold text-black">{isLoading ? "—" : value}</p>
    </div>
  );
}

export default function Dashboard() {
  const [kpis, setKpis] = useState(null);
  const [overdue, setOverdue] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [kpiRes, overdueRes] = await Promise.all([
        api.get("/dashboard/kpis"),
        api.get("/dashboard/overdue-returns"),
      ]);
      setKpis(kpiRes.data);
      setOverdue(overdueRes.data.items);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to load dashboard data.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    // Light polling keeps the KPI cards reasonably fresh without a websocket layer.
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  return (
    <div className="p-8">
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-2xl font-bold text-black">Dashboard</h2>
        <button
          onClick={fetchData}
          className="rounded-md border border-black px-3 py-1.5 text-sm font-medium text-black hover:bg-black hover:text-white"
        >
          Refresh
        </button>
      </div>

      {error && (
        <div className="mb-6 rounded-md border border-black bg-white p-4 text-sm text-black">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard label="Assets Available" value={kpis?.assets_available} isLoading={isLoading} />
        <KpiCard label="Assets Allocated" value={kpis?.assets_allocated} isLoading={isLoading} />
        <KpiCard label="Maintenance Today" value={kpis?.maintenance_today} isLoading={isLoading} />
        <KpiCard label="Active Bookings" value={kpis?.active_bookings} isLoading={isLoading} />
        <KpiCard label="Pending Transfers" value={kpis?.pending_transfers} isLoading={isLoading} />
        <KpiCard label="Upcoming Returns" value={kpis?.upcoming_returns} isLoading={isLoading} />
        <KpiCard label="Overdue Returns" value={kpis?.overdue_returns} isLoading={isLoading} />
      </div>

      <div className="mt-8">
        <h3 className="mb-3 text-lg font-semibold text-black">Overdue Returns</h3>
        <div className="overflow-hidden rounded-lg border border-gray-300 bg-white">
          {isLoading ? (
            <p className="p-6 text-sm text-gray-500">Loading…</p>
          ) : overdue.length === 0 ? (
            <p className="p-6 text-sm text-gray-500">Nothing overdue right now.</p>
          ) : (
            <table className="w-full text-left text-sm">
              <thead className="border-b border-gray-300 bg-gray-50">
                <tr>
                  <th className="px-4 py-3 font-semibold text-black">Resource</th>
                  <th className="px-4 py-3 font-semibold text-black">Held By</th>
                  <th className="px-4 py-3 font-semibold text-black">Was Due</th>
                  <th className="px-4 py-3 font-semibold text-black">Overdue By</th>
                </tr>
              </thead>
              <tbody>
                {overdue.map((b) => (
                  <tr key={b.id} className="border-b border-gray-200 last:border-0">
                    <td className="px-4 py-3 text-black">
                      {b.resource?.asset_tag} · {b.resource?.name}
                    </td>
                    <td className="px-4 py-3 text-black">{b.employee?.full_name}</td>
                    <td className="px-4 py-3 text-gray-600">
                      {new Date(b.end_time).toLocaleString()}
                    </td>
                    <td className="px-4 py-3 font-medium text-black">{b.hours_overdue}h</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
