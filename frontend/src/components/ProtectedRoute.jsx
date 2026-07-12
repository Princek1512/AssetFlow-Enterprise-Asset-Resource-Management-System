import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthProvider";
import AccessDenied from "../pages/AccessDenied";

export default function ProtectedRoute({ children, roles }) {
  const { isAuthenticated, hasRole, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-white text-black">
        <p className="text-sm tracking-wide">Loading…</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (roles && roles.length > 0 && !hasRole(...roles)) {
    return <AccessDenied />;
  }

  return children;
}
