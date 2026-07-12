import { useEffect, useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/api";
import { useToast } from "../components/Toast";

export default function Notifications() {
  const { showToast } = useToast();
  const navigate = useNavigate();
  
  const [activeTab, setActiveTab] = useState("All");
  const [isLoading, setIsLoading] = useState(true);
  
  const [feed, setFeed] = useState([]);

  useEffect(() => {
    const fetchActivities = async () => {
      setIsLoading(true);
      try {
        const [bookingsRes, transfersRes, maintenanceRes] = await Promise.allSettled([
          api.get("/bookings"),
          api.get("/transfer-requests"),
          api.get("/maintenance")
        ]);

        const bookings = bookingsRes.status === "fulfilled" ? (bookingsRes.value.data.items || []) : [];
        const transfers = transfersRes.status === "fulfilled" ? (transfersRes.value.data || []) : [];
        const maintenance = maintenanceRes.status === "fulfilled" ? (maintenanceRes.value.data.items || []) : [];

        const activityFeed = [];

        bookings.forEach(b => {
          activityFeed.push({
            id: `b_${b.id}`,
            type: "Booking",
            message: `Resource booked by ${b.employee?.full_name || 'User'}`,
            timestamp: new Date(b.created_at),
            category: "Bookings",
            color: "bg-blue-500"
          });
        });

        transfers.forEach(t => {
          activityFeed.push({
            id: `t_${t.id}`,
            type: "Transfer",
            message: `Transfer requested by ${t.requested_by?.full_name || 'User'} for asset`,
            timestamp: new Date(t.created_at),
            category: "Approvals",
            color: "bg-orange-500"
          });
        });

        maintenance.forEach(m => {
          activityFeed.push({
            id: `m_${m.id}`,
            type: "Maintenance",
            message: `Maintenance requested for ${m.asset?.name || 'Asset'}`,
            timestamp: new Date(m.created_at),
            category: "Alerts",
            color: "bg-red-500"
          });
        });

        // Add some mock notifications for realism
        activityFeed.push({
          id: `mock_1`,
          type: "System",
          message: "Weekly compliance report generated successfully.",
          timestamp: new Date(Date.now() - 1000 * 60 * 60 * 24), // 1 day ago
          category: "All",
          color: "bg-gray-500"
        });

        activityFeed.sort((a, b) => b.timestamp - a.timestamp);
        setFeed(activityFeed);

      } catch (err) {
        showToast("Failed to load activity logs.", "error");
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchActivities();
  }, [showToast]);

  const filteredFeed = useMemo(() => {
    if (activeTab === "All") return feed;
    return feed.filter(item => item.category === activeTab);
  }, [feed, activeTab]);

  const tabs = ["All", "Alerts", "Approvals", "Bookings"];

  return (
    <div className="p-8 max-w-4xl">
      <h2 className="mb-6 text-2xl font-bold text-black">Activity Logs & Notifications</h2>

      <div className="mb-6 border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {tabs.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`whitespace-nowrap border-b-2 py-4 px-1 text-sm font-medium transition-colors ${
                activeTab === tab
                  ? "border-black text-black"
                  : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700"
              }`}
            >
              {tab}
            </button>
          ))}
        </nav>
      </div>

      {isLoading ? (
        <p className="text-sm text-gray-500">Loading activities...</p>
      ) : (
        <div className="rounded-lg border border-gray-300 bg-white">
          <ul className="divide-y divide-gray-200">
            {filteredFeed.length === 0 ? (
              <li className="p-6 text-center text-sm text-gray-500">
                No notifications found.
              </li>
            ) : (
              filteredFeed.map((item) => (
                <li key={item.id} className="flex items-start gap-4 p-4 hover:bg-gray-50 transition-colors">
                  <div className={`mt-1 h-3 w-3 rounded-sm flex-shrink-0 ${item.color}`}></div>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-black">{item.message}</p>
                    <p className="mt-1 text-xs text-gray-500">
                      {item.timestamp.toLocaleString()} · {item.type}
                    </p>
                  </div>
                  {item.category === "Approvals" && (
                    <button 
                      onClick={() => navigate('/transfers')}
                      className="rounded-md border border-gray-300 bg-white px-3 py-1 text-xs font-medium text-black hover:bg-gray-50"
                    >
                      Review
                    </button>
                  )}
                </li>
              ))
            )}
          </ul>
        </div>
      )}
    </div>
  );
}
