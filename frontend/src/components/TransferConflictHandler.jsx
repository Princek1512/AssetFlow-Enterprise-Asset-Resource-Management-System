import { useState } from "react";
import api from "../api/api";
import { useToast } from "./Toast";

export default function TransferConflictHandler({ assetId, currentHolderId, onClose, onTransferRequested }) {
  const { showToast } = useToast();
  const [reason, setReason] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleRequestTransfer = async () => {
    setIsSubmitting(true);
    try {
      await api.post(`/assets/${assetId}/transfer-requests`, { reason });
      showToast("Transfer requested successfully.");
      onTransferRequested();
      onClose();
    } catch (err) {
      showToast(err.response?.data?.detail || "Failed to request transfer.", "error");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="mt-4 border-t border-gray-200 pt-4">
      <div className="rounded-md bg-yellow-50 p-4 border border-yellow-200">
        <h4 className="text-sm font-medium text-yellow-800">Allocation Conflict (409)</h4>
        <p className="mt-1 text-xs text-yellow-700">
          This asset is currently allocated to user ID: {currentHolderId}. 
          Would you like to request a transfer?
        </p>
        <div className="mt-3">
          <input
            type="text"
            placeholder="Reason for transfer..."
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-yellow-500 focus:outline-none"
          />
        </div>
        <div className="mt-3 flex gap-2">
          <button
            onClick={handleRequestTransfer}
            disabled={isSubmitting || !reason.trim()}
            className="rounded-md bg-yellow-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-yellow-700 disabled:opacity-50"
          >
            {isSubmitting ? "Requesting..." : "Request Transfer"}
          </button>
          <button
            onClick={onClose}
            className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
