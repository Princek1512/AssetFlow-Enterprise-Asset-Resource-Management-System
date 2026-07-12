import { NavLink } from "react-router-dom";
import { useAuth } from "../context/AuthProvider";

// Tabs match the Excalidraw mockup. `roles: null` means every authenticated
// role can see the tab; otherwise it's restricted to the listed roles.
const NAV_ITEMS = [
  { label: "Dashboard", path: "/", roles: null },
  { label: "Organization setup", path: "/admin", roles: ["admin"] },
  { label: "Asset Categories", path: "/categories", roles: ["admin", "asset_manager"] },
  { label: "Assets", path: "/assets", roles: null },
  { label: "Allocation & Transfer", path: "/transfers", roles: ["admin", "asset_manager", "department_head"] },
  { label: "Resource Booking", path: "/bookings", roles: null },
  { label: "Maintenance", path: "/maintenance", roles: null },
  { label: "Audit", path: "/audit", roles: ["admin", "asset_manager"] },
  { label: "Reports", path: "/reports", roles: ["admin", "asset_manager"] },
  { label: "Notifications", path: "/notifications", roles: null },
];

export default function Sidebar() {
  const { user, hasRole, logout } = useAuth();

  const visibleItems = NAV_ITEMS.filter((item) => !item.roles || hasRole(...item.roles));

  return (
    <aside className="flex h-screen w-64 flex-col border-r border-gray-300 bg-white">
      <div className="border-b border-gray-300 px-6 py-5">
        <h1 className="text-lg font-bold tracking-tight text-black">AssetFlow</h1>
        <p className="mt-0.5 text-xs text-gray-500">Asset & Resource Management</p>
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
        {visibleItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === "/"}
            className={({ isActive }) =>
              [
                "block rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-black text-white"
                  : "text-black hover:bg-gray-100 border border-transparent hover:border-gray-300",
              ].join(" ")
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-gray-300 px-4 py-4">
        <div className="mb-3">
          <p className="truncate text-sm font-semibold text-black">{user?.full_name}</p>
          <p className="truncate text-xs text-gray-500">{user?.role?.replace("_", " ")}</p>
        </div>
        <button
          onClick={logout}
          className="w-full rounded-md border border-black bg-white px-3 py-2 text-sm font-medium text-black transition-colors hover:bg-black hover:text-white"
        >
          Log out
        </button>
      </div>
    </aside>
  );
}
