import { useEffect, useState, useCallback } from "react";
import api from "../api/api";
import { useToast } from "../components/Toast";

const PROMOTABLE_ROLES = ["asset_manager", "department_head", "employee"];

export default function Admin() {
  const { showToast } = useToast();
  const [users, setUsers] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  const fetchUsers = useCallback(async () => {
    setIsLoading(true);
    try {
      const { data } = await api.get("/admin/users");
      setUsers(data);
    } catch {
      showToast("Failed to load users.", "error");
    } finally {
      setIsLoading(false);
    }
  }, [showToast]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const handlePromote = async (userId, role) => {
    try {
      await api.post(`/admin/users/${userId}/promote`, { role });
      showToast("Role updated.");
      fetchUsers();
    } catch (err) {
      showToast(err.response?.data?.detail || "Could not update role.", "error");
    }
  };

  const handleDeactivate = async (userId) => {
    try {
      await api.patch(`/admin/users/${userId}/deactivate`);
      showToast("User deactivated.");
      fetchUsers();
    } catch (err) {
      showToast(err.response?.data?.detail || "Could not deactivate user.", "error");
    }
  };

  return (
    <div className="p-8">
      <h2 className="mb-6 text-2xl font-bold text-black">Admin — Users</h2>

      <div className="overflow-x-auto rounded-lg border border-gray-300 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-gray-300 bg-gray-50">
            <tr>
              <th className="px-4 py-3 font-semibold text-black">Name</th>
              <th className="px-4 py-3 font-semibold text-black">Email</th>
              <th className="px-4 py-3 font-semibold text-black">Role</th>
              <th className="px-4 py-3 font-semibold text-black">Status</th>
              <th className="px-4 py-3 font-semibold text-black">Change Role</th>
              <th className="px-4 py-3 font-semibold text-black"></th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-gray-500">
                  Loading…
                </td>
              </tr>
            ) : users.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-gray-500">
                  No users found.
                </td>
              </tr>
            ) : (
              users.map((u) => (
                <tr key={u.id} className="border-b border-gray-200 last:border-0">
                  <td className="px-4 py-3 text-black">{u.full_name}</td>
                  <td className="px-4 py-3 text-gray-600">{u.email}</td>
                  <td className="px-4 py-3">
                    <span className="rounded border border-black px-2 py-0.5 text-xs uppercase text-black">
                      {u.role.replace("_", " ")}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-xs text-gray-600">
                      {u.is_active ? "Active" : "Deactivated"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {u.role !== "admin" && (
                      <select
                        defaultValue=""
                        onChange={(e) => {
                          if (e.target.value) handlePromote(u.id, e.target.value);
                          e.target.value = "";
                        }}
                        className="rounded-md border border-gray-300 bg-white px-2 py-1 text-xs text-black"
                      >
                        <option value="" disabled>
                          Set role…
                        </option>
                        {PROMOTABLE_ROLES.filter((r) => r !== u.role).map((r) => (
                          <option key={r} value={r}>
                            {r.replace("_", " ")}
                          </option>
                        ))}
                      </select>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {u.is_active && u.role !== "admin" && (
                      <button
                        onClick={() => handleDeactivate(u.id)}
                        className="text-xs font-medium text-black underline hover:no-underline"
                      >
                        Deactivate
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
  );
}
