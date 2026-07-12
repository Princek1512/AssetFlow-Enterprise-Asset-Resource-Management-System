import { ShieldAlert } from "lucide-react";
import { Link } from "react-router-dom";

export default function AccessDenied() {
  return (
    <div className="flex h-screen flex-col items-center justify-center bg-gray-50 p-6 text-center">
      <ShieldAlert className="mb-6 h-16 w-16 text-black" />
      <h1 className="mb-2 text-3xl font-bold tracking-tight text-black">Access Denied</h1>
      <p className="mb-8 max-w-md text-sm text-gray-600">
        You do not have the required role permissions to view this page. If you believe this is an error, please contact your system administrator.
      </p>
      <Link
        to="/"
        className="rounded-md border border-black bg-black px-6 py-2 text-sm font-medium text-white transition-colors hover:bg-gray-800 hover:text-white"
      >
        Return to Dashboard
      </Link>
    </div>
  );
}
