import { useEffect, useState, useRef, useCallback } from "react";
import api from "../api/api";
import { useToast } from "../components/Toast";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip as RechartsTooltip, ResponsiveContainer,
  LineChart, Line, PieChart, Pie, Cell
} from "recharts";
import jsPDF from "jspdf";
import html2canvas from "html2canvas";
import { Download } from "lucide-react";

const PIE_COLORS = ["#000000", "#4B5563", "#9CA3AF", "#D1D5DB", "#E5E7EB", "#F3F4F6"];

export default function Reports() {
  const { showToast } = useToast();
  const reportRef = useRef(null);

  const [isLoading, setIsLoading] = useState(true);

  const [utilizationData, setUtilizationData] = useState([]);
  const [maintenanceData, setMaintenanceData] = useState([]);
  const [statusDistribution, setStatusDistribution] = useState([]);
  const [mostUsed, setMostUsed] = useState([]);
  const [idle, setIdle] = useState([]);
  const [dueMaintenance, setDueMaintenance] = useState([]);

  const fetchReportData = useCallback(async () => {
    setIsLoading(true);
    try {
      // Fetch each individually so one failure doesn't break all
      const [assetsRes, bookingsRes, maintenanceRes, categoriesRes] = await Promise.allSettled([
        api.get("/assets", { params: { limit: 1000 } }),
        api.get("/bookings"),
        api.get("/maintenance"),
        api.get("/asset-categories"),
      ]);

      const assets =
        assetsRes.status === "fulfilled" ? assetsRes.value.data.items || [] : [];
      const bookings =
        bookingsRes.status === "fulfilled" ? bookingsRes.value.data.items || [] : [];
      const mReqs =
        maintenanceRes.status === "fulfilled"
          ? maintenanceRes.value.data.items || []
          : [];
      const rawCats =
        categoriesRes.status === "fulfilled" ? categoriesRes.value.data : null;
      const categories = rawCats
        ? Array.isArray(rawCats)
          ? rawCats
          : rawCats.items || []
        : [];

      // 1. Utilization by Category (Bar Chart)
      const catMap = {};
      categories.forEach(c => (catMap[c.id] = c.name));

      const utilMap = {};
      // Count assets per category for utilization
      assets.forEach(a => {
        if (a.category_id) {
          const catName = catMap[a.category_id] || "Unknown";
          utilMap[catName] = (utilMap[catName] || 0) + 1;
        }
      });

      const uData = Object.keys(utilMap).map(k => ({
        name: k,
        assets: utilMap[k],
      }));
      setUtilizationData(uData.length > 0 ? uData : [{ name: "No Data", assets: 0 }]);

      // 2. Status Distribution (Pie Chart)
      const statusMap = {};
      assets.forEach(a => {
        const s = a.status || "unknown";
        statusMap[s] = (statusMap[s] || 0) + 1;
      });
      const sDist = Object.keys(statusMap).map(k => ({
        name: k.replace("_", " "),
        value: statusMap[k],
      }));
      setStatusDistribution(sDist);

      // 3. Maintenance Frequency (Line Chart)
      const mFreq = {};
      mReqs.forEach(req => {
        const d = new Date(req.created_at);
        const month = d.toLocaleString("default", { month: "short" });
        mFreq[month] = (mFreq[month] || 0) + 1;
      });

      const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"];
      const mData = months.map(m => ({ name: m, issues: mFreq[m] || 0 }));
      setMaintenanceData(mData);

      // 4. Most used / Idle
      const assetUsage = {};
      bookings.forEach(b => {
        assetUsage[b.resource_id] = (assetUsage[b.resource_id] || 0) + 1;
      });

      const sortedAssets = [...assets]
        .map(a => ({
          ...a,
          usageCount: assetUsage[a.id] || 0,
        }))
        .sort((a, b) => b.usageCount - a.usageCount);

      setMostUsed(sortedAssets.slice(0, 3));
      setIdle(sortedAssets.filter(a => a.usageCount === 0).slice(0, 3));

      // 5. Due for maintenance
      const due = assets
        .filter(a => a.condition === "poor" || a.condition === "fair" || a.condition === "damaged")
        .slice(0, 3);
      setDueMaintenance(due);
    } catch (err) {
      showToast("Failed to load report data.", "error");
    } finally {
      setIsLoading(false);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    fetchReportData();
  }, [fetchReportData]);

  const exportPDF = async () => {
    if (!reportRef.current) return;
    try {
      const canvas = await html2canvas(reportRef.current, {
        scale: 2,
        backgroundColor: "#ffffff",
      });
      const imgData = canvas.toDataURL("image/png");
      const pdf = new jsPDF("p", "mm", "a4");

      const pdfWidth = pdf.internal.pageSize.getWidth();
      const pdfHeight = (canvas.height * pdfWidth) / canvas.width;

      pdf.addImage(imgData, "PNG", 0, 0, pdfWidth, pdfHeight);
      pdf.save("AssetFlow_Report.pdf");
    } catch (err) {
      showToast("Failed to generate PDF", "error");
    }
  };

  if (isLoading) {
    return <div className="p-8 text-gray-500">Generating report data...</div>;
  }

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <div className="mb-8 flex items-center justify-between">
        <h2 className="text-2xl font-bold text-black">Reports & Analytics</h2>
        <button
          onClick={exportPDF}
          className="flex items-center gap-2 rounded-md bg-black px-4 py-2 text-sm font-medium text-white hover:bg-gray-800"
        >
          <Download className="h-4 w-4" />
          Export Report
        </button>
      </div>

      <div ref={reportRef} className="space-y-8 bg-white p-2">
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
          {/* Bar Chart — Assets per Category */}
          <div className="rounded-lg border border-gray-300 p-6 shadow-sm">
            <h3 className="mb-6 text-lg font-bold text-black">Assets by Category</h3>
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={utilizationData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
                  <XAxis
                    dataKey="name"
                    axisLine={false}
                    tickLine={false}
                    tick={{ fontSize: 12, fill: "#6B7280" }}
                    dy={10}
                  />
                  <YAxis
                    axisLine={false}
                    tickLine={false}
                    tick={{ fontSize: 12, fill: "#6B7280" }}
                  />
                  <RechartsTooltip
                    cursor={{ fill: "#F3F4F6" }}
                    contentStyle={{
                      borderRadius: "8px",
                      border: "1px solid #E5E7EB",
                      boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)",
                    }}
                  />
                  <Bar dataKey="assets" fill="#000000" radius={[4, 4, 0, 0]} barSize={40} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Pie Chart — Status Distribution */}
          <div className="rounded-lg border border-gray-300 p-6 shadow-sm">
            <h3 className="mb-6 text-lg font-bold text-black">Asset Status Distribution</h3>
            <div className="h-64 w-full">
              {statusDistribution.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={statusDistribution}
                      cx="50%"
                      cy="50%"
                      innerRadius={50}
                      outerRadius={90}
                      paddingAngle={2}
                      dataKey="value"
                      label={({ name, value }) => `${name} (${value})`}
                    >
                      {statusDistribution.map((_, index) => (
                        <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <RechartsTooltip
                      contentStyle={{
                        borderRadius: "8px",
                        border: "1px solid #E5E7EB",
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <p className="flex h-full items-center justify-center text-sm text-gray-500">
                  No data
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Line Chart — Maintenance */}
        <div className="rounded-lg border border-gray-300 p-6 shadow-sm">
          <h3 className="mb-6 text-lg font-bold text-black">Maintenance Frequency</h3>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={maintenanceData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
                <XAxis
                  dataKey="name"
                  axisLine={false}
                  tickLine={false}
                  tick={{ fontSize: 12, fill: "#6B7280" }}
                  dy={10}
                />
                <YAxis
                  axisLine={false}
                  tickLine={false}
                  tick={{ fontSize: 12, fill: "#6B7280" }}
                />
                <RechartsTooltip
                  contentStyle={{
                    borderRadius: "8px",
                    border: "1px solid #E5E7EB",
                    boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)",
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="issues"
                  stroke="#000000"
                  strokeWidth={3}
                  dot={{ r: 4, fill: "#000000", strokeWidth: 0 }}
                  activeDot={{ r: 6 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Text Lists Area */}
        <div className="grid grid-cols-1 gap-8 md:grid-cols-3">
          <div className="rounded-lg border border-gray-300 p-6 shadow-sm">
            <h3 className="mb-4 text-sm font-bold uppercase tracking-wider text-black">
              Most Used Assets
            </h3>
            <ul className="space-y-4">
              {mostUsed.length === 0 ? (
                <p className="text-sm text-gray-500">No data</p>
              ) : (
                mostUsed.map(a => (
                  <li
                    key={a.id}
                    className="flex justify-between items-center border-b border-gray-100 pb-2 last:border-0 last:pb-0"
                  >
                    <div>
                      <p className="text-sm font-semibold text-black">{a.name}</p>
                      <p className="text-xs text-gray-500 font-mono">{a.asset_tag}</p>
                    </div>
                    <span className="text-xs font-bold bg-gray-100 px-2 py-1 rounded">
                      {a.usageCount} bookings
                    </span>
                  </li>
                ))
              )}
            </ul>
          </div>

          <div className="rounded-lg border border-gray-300 p-6 shadow-sm">
            <h3 className="mb-4 text-sm font-bold uppercase tracking-wider text-black">
              Idle Assets
            </h3>
            <ul className="space-y-4">
              {idle.length === 0 ? (
                <p className="text-sm text-gray-500">No idle assets</p>
              ) : (
                idle.map(a => (
                  <li
                    key={a.id}
                    className="flex justify-between items-center border-b border-gray-100 pb-2 last:border-0 last:pb-0"
                  >
                    <div>
                      <p className="text-sm font-semibold text-black">{a.name}</p>
                      <p className="text-xs text-gray-500 font-mono">{a.asset_tag}</p>
                    </div>
                    <span className="text-[10px] uppercase font-bold text-gray-500 border border-gray-300 px-2 py-0.5 rounded">
                      Inactive
                    </span>
                  </li>
                ))
              )}
            </ul>
          </div>

          <div className="rounded-lg border border-red-200 bg-red-50 p-6 shadow-sm">
            <h3 className="mb-4 text-sm font-bold uppercase tracking-wider text-red-900">
              Due for Maintenance
            </h3>
            <ul className="space-y-4">
              {dueMaintenance.length === 0 ? (
                <p className="text-sm text-red-700">All good!</p>
              ) : (
                dueMaintenance.map(a => (
                  <li
                    key={a.id}
                    className="flex justify-between items-center border-b border-red-100 pb-2 last:border-0 last:pb-0"
                  >
                    <div>
                      <p className="text-sm font-semibold text-red-900">{a.name}</p>
                      <p className="text-xs text-red-700 font-mono">{a.asset_tag}</p>
                    </div>
                    <span className="text-[10px] uppercase font-bold text-red-700 border border-red-300 bg-red-100 px-2 py-0.5 rounded">
                      {a.condition} condition
                    </span>
                  </li>
                ))
              )}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
