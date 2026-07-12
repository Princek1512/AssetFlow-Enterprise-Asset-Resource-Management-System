import { useEffect, useState, useCallback, useMemo } from "react";
import api from "../api/api";
import { useToast } from "../components/Toast";
import { useAuth } from "../context/AuthProvider";
import { ChevronDown, Calendar, Clock, AlertCircle } from "lucide-react";

export default function ResourceBooking() {
  const { showToast } = useToast();
  const { hasRole } = useAuth();
  const canManage = hasRole("admin", "asset_manager");

  const [resources, setResources] = useState([]);
  const [bookings, setBookings] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  const [selectedResourceId, setSelectedResourceId] = useState("");
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split("T")[0]);

  const [form, setForm] = useState({ start_time: "", end_time: "", is_permanent: false });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isBookingModalOpen, setIsBookingModalOpen] = useState(false);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [assetsRes, bookingsRes] = await Promise.all([
        api.get("/assets", { params: { is_bookable: true } }),
        api.get("/bookings"),
      ]);
      setResources(assetsRes.data.items || []);
      setBookings(bookingsRes.data.items || []);

      if (assetsRes.data.items?.length > 0 && !selectedResourceId) {
        setSelectedResourceId(assetsRes.data.items[0].id);
      }
    } catch {
      showToast("Failed to load booking data.", "error");
    } finally {
      setIsLoading(false);
    }
  }, [showToast, selectedResourceId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const selectedResource = useMemo(() => {
    return resources.find(r => r.id === selectedResourceId);
  }, [resources, selectedResourceId]);

  const filteredBookings = useMemo(() => {
    return bookings.filter(b => {
      const bDate = new Date(b.start_time).toISOString().split("T")[0];
      return b.resource_id === selectedResourceId && bDate === selectedDate;
    });
  }, [bookings, selectedResourceId, selectedDate]);

  // All bookings for selected resource (for the management table)
  const resourceBookings = useMemo(() => {
    return bookings.filter(b => b.resource_id === selectedResourceId);
  }, [bookings, selectedResourceId]);

  const openBookingForm = () => {
    setForm({ start_time: "", end_time: "", is_permanent: false });
    setIsBookingModalOpen(true);
  };

  const handleBook = async (e) => {
    e.preventDefault();
    if (!selectedResource) return;
    setIsSubmitting(true);
    try {
      const payload = {
        resource_id: selectedResource.id,
        start_time: new Date(form.start_time).toISOString(),
        is_permanent: form.is_permanent,
      };

      if (!form.is_permanent) {
        payload.end_time = new Date(form.end_time).toISOString();
      }

      await api.post("/bookings", payload);
      showToast(`Booked ${selectedResource.name}.`);
      setIsBookingModalOpen(false);
      fetchData();
    } catch (err) {
      const detail = err.response?.data?.detail;
      const message = typeof detail === "string" ? detail : detail?.message || "Booking failed.";
      showToast(message, "error");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancelBooking = async (bookingId) => {
    try {
      await api.post(`/bookings/${bookingId}/cancel`);
      showToast("Booking cancelled.");
      fetchData();
    } catch (err) {
      showToast(err.response?.data?.detail || "Failed to cancel booking.", "error");
    }
  };

  const renderTimeline = () => {
    const startHour = 9;
    const endHour = 17;
    const totalHours = endHour - startHour;

    return (
      <div className="relative mt-8 h-40 w-full rounded-md border border-gray-300 bg-gray-50">
        {/* Grid lines */}
        <div className="absolute inset-0 flex">
          {Array.from({ length: totalHours + 1 }).map((_, i) => (
            <div key={i} className="relative flex-1 border-l border-gray-200 first:border-l-0">
              <span className="absolute -top-6 left-0 -translate-x-1/2 text-xs font-medium text-gray-500">
                {startHour + i}:00
              </span>
            </div>
          ))}
        </div>

        {/* Bookings */}
        {filteredBookings.map(b => {
          const sTime = new Date(b.start_time);
          const eTime = new Date(b.end_time);

          let sHour = sTime.getHours() + sTime.getMinutes() / 60;
          let eHour = eTime.getHours() + eTime.getMinutes() / 60;

          if (b.is_permanent || eTime.getFullYear() === 2099) {
            eHour = endHour;
          }

          if (sHour < startHour) sHour = startHour;
          if (eHour > endHour) eHour = endHour;

          const leftPercent = ((sHour - startHour) / totalHours) * 100;
          const widthPercent = ((eHour - sHour) / totalHours) * 100;

          if (leftPercent >= 100 || leftPercent + widthPercent <= 0) return null;

          const isConflict = b.status === "requested";

          return (
            <div
              key={b.id}
              className={`absolute top-4 bottom-4 rounded-md border p-2 text-xs ${
                isConflict
                  ? "border-dashed border-red-500 bg-red-50 text-red-700"
                  : "border-black bg-black text-white"
              }`}
              style={{
                left: `${Math.max(0, leftPercent)}%`,
                width: `${Math.min(100 - leftPercent, widthPercent)}%`,
              }}
            >
              <p className="truncate font-semibold">{b.employee?.full_name}</p>
              <p className="truncate opacity-80">
                {sTime.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} -{" "}
                {eTime.getFullYear() === 2099
                  ? " Permanent"
                  : eTime.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              </p>
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div className="p-8">
      <div className="mb-8 flex items-center justify-between">
        <h2 className="text-2xl font-bold text-black">Resource Booking</h2>
        <button
          onClick={openBookingForm}
          className="rounded-md bg-black px-4 py-2 text-sm font-medium text-white hover:bg-gray-800"
        >
          New Booking
        </button>
      </div>

      <div className="mb-6 flex gap-4">
        <div className="w-1/3">
          <label className="mb-1 block text-sm font-medium text-gray-700">Select Resource</label>
          <div className="relative">
            <select
              value={selectedResourceId}
              onChange={(e) => setSelectedResourceId(e.target.value)}
              className="w-full appearance-none rounded-md border border-gray-300 bg-white px-4 py-2 pr-10 text-sm text-black focus:border-black focus:outline-none focus:ring-1 focus:ring-black"
            >
              {resources.map(r => (
                <option key={r.id} value={r.id}>
                  {r.name} ({r.asset_tag})
                </option>
              ))}
            </select>
            <ChevronDown className="absolute right-3 top-2.5 h-4 w-4 text-gray-500 pointer-events-none" />
          </div>
        </div>

        <div className="w-1/3">
          <label className="mb-1 block text-sm font-medium text-gray-700">Date</label>
          <div className="relative">
            <input
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="w-full rounded-md border border-gray-300 bg-white px-4 py-2 text-sm text-black focus:border-black focus:outline-none focus:ring-1 focus:ring-black"
            />
          </div>
        </div>
      </div>

      {isLoading ? (
        <p className="text-sm text-gray-500">Loading timeline...</p>
      ) : (
        <>
          <div className="rounded-lg border border-gray-300 bg-white p-8 pt-12 shadow-sm">
            {renderTimeline()}
            <div className="mt-8 flex gap-6 text-sm text-gray-600">
              <div className="flex items-center gap-2">
                <div className="h-4 w-4 rounded bg-black"></div>
                <span>Confirmed Booking</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="h-4 w-4 rounded border-2 border-dashed border-red-500 bg-red-50"></div>
                <span>Conflict / Requested</span>
              </div>
            </div>
          </div>

          {/* Booking Management Table */}
          <div className="mt-8">
            <h3 className="mb-4 text-lg font-semibold text-black">
              Bookings for this Resource
            </h3>
            <div className="overflow-x-auto rounded-lg border border-gray-300 bg-white">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-gray-300 bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 font-semibold text-black">Employee</th>
                    <th className="px-4 py-3 font-semibold text-black">Start</th>
                    <th className="px-4 py-3 font-semibold text-black">End</th>
                    <th className="px-4 py-3 font-semibold text-black">Status</th>
                    <th className="px-4 py-3 font-semibold text-black text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {resourceBookings.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-4 py-6 text-center text-gray-500">
                        No bookings for this resource.
                      </td>
                    </tr>
                  ) : (
                    resourceBookings.map(b => (
                      <tr key={b.id} className="border-b border-gray-200 last:border-0">
                        <td className="px-4 py-3 text-black">{b.employee?.full_name || "—"}</td>
                        <td className="px-4 py-3 text-gray-600">
                          {new Date(b.start_time).toLocaleString()}
                        </td>
                        <td className="px-4 py-3 text-gray-600">
                          {new Date(b.end_time).getFullYear() === 2099
                            ? "Permanent"
                            : new Date(b.end_time).toLocaleString()}
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={`rounded border px-2 py-0.5 text-xs uppercase ${
                              b.status === "cancelled"
                                ? "border-red-300 text-red-700 bg-red-50"
                                : b.status === "completed"
                                ? "border-green-300 text-green-700 bg-green-50"
                                : "border-black text-black"
                            }`}
                          >
                            {b.status}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right">
                          {(b.status === "upcoming" || b.status === "ongoing") && canManage && (
                            <button
                              onClick={() => handleCancelBooking(b.id)}
                              className="rounded-md border border-red-600 bg-white px-3 py-1 text-xs font-medium text-red-600 hover:bg-red-50"
                            >
                              Cancel Booking
                            </button>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {isBookingModalOpen && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-md rounded-lg border border-gray-300 bg-white p-6 shadow-xl">
            <div className="mb-6 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-black">Book Resource</h3>
              <button
                onClick={() => setIsBookingModalOpen(false)}
                className="text-gray-400 hover:text-black"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleBook} className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-gray-700">Resource</label>
                <input
                  type="text"
                  disabled
                  value={selectedResource?.name || ""}
                  className="mt-1 w-full rounded-md border border-gray-300 bg-gray-50 px-3 py-2 text-sm text-gray-600"
                />
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="is_permanent"
                  checked={form.is_permanent}
                  onChange={(e) => setForm({ ...form, is_permanent: e.target.checked })}
                  className="h-4 w-4 rounded border-gray-300 text-black focus:ring-black"
                />
                <label htmlFor="is_permanent" className="text-sm font-medium text-black">
                  Permanent Allocation
                </label>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Start Time</label>
                  <input
                    required
                    type="datetime-local"
                    value={form.start_time}
                    onChange={(e) => setForm({ ...form, start_time: e.target.value })}
                    className="mt-1 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-black focus:border-black focus:outline-none focus:ring-1 focus:ring-black"
                  />
                </div>

                {!form.is_permanent && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700">End Time</label>
                    <input
                      required={!form.is_permanent}
                      type="datetime-local"
                      value={form.end_time}
                      onChange={(e) => setForm({ ...form, end_time: e.target.value })}
                      className="mt-1 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-black focus:border-black focus:outline-none focus:ring-1 focus:ring-black"
                    />
                  </div>
                )}
              </div>

              <div className="mt-6 flex justify-end gap-3 pt-4 border-t border-gray-100">
                <button
                  type="button"
                  onClick={() => setIsBookingModalOpen(false)}
                  className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-black hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="rounded-md bg-black px-4 py-2 text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-50"
                >
                  {isSubmitting ? "Booking..." : "Confirm Booking"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
