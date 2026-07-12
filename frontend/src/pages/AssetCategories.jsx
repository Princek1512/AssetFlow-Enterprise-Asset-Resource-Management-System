import { useEffect, useState, useCallback } from "react";
import api from "../api/api";
import { useToast } from "../components/Toast";

export default function AssetCategories() {
  const { showToast } = useToast();
  const [categories, setCategories] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [form, setForm] = useState({ name: "", description: "" });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const fetchCategories = useCallback(async () => {
    setIsLoading(true);
    try {
      const { data } = await api.get("/asset-categories");
      setCategories(data.items ?? data);
    } catch {
      showToast("Failed to load categories.", "error");
    } finally {
      setIsLoading(false);
    }
  }, [showToast]);

  useEffect(() => {
    fetchCategories();
  }, [fetchCategories]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      await api.post("/asset-categories", {
        name: form.name,
        description: form.description || null,
      });
      showToast("Category created.");
      setForm({ name: "", description: "" });
      setIsModalOpen(false);
      fetchCategories();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to create category.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (categoryId) => {
    try {
      await api.delete(`/asset-categories/${categoryId}`);
      showToast("Category deleted.");
      fetchCategories();
    } catch (err) {
      showToast(err.response?.data?.detail || "Could not delete category.", "error");
    }
  };

  return (
    <div className="p-8">
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-2xl font-bold text-black">Asset Categories</h2>
        <button
          onClick={() => setIsModalOpen(true)}
          className="rounded-md bg-black px-4 py-2 text-sm font-medium text-white hover:bg-gray-800"
        >
          + New Category
        </button>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {isLoading ? (
          <p className="text-sm text-gray-500">Loading…</p>
        ) : categories.length === 0 ? (
          <p className="col-span-full text-sm text-gray-500">No categories yet.</p>
        ) : (
          categories.map((c) => (
            <div key={c.id} className="rounded-lg border border-gray-300 bg-white p-5">
              <div className="flex items-start justify-between">
                <p className="text-base font-semibold text-black">{c.name}</p>
                <button
                  onClick={() => handleDelete(c.id)}
                  className="text-xs font-medium text-black underline hover:no-underline"
                >
                  Delete
                </button>
              </div>
              <p className="mt-1 text-sm text-gray-500">{c.description || "No description."}</p>
            </div>
          ))
        )}
      </div>

      {isModalOpen && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-md rounded-lg border border-gray-300 bg-white p-6">
            <h3 className="mb-4 text-lg font-semibold text-black">New Category</h3>

            {error && (
              <div className="mb-4 rounded-md border border-black p-3 text-sm text-black">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-gray-600">Name</label>
                <input
                  required
                  minLength={2}
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="mt-1 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-black focus:border-black"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-600">Description</label>
                <textarea
                  rows={3}
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  className="mt-1 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-black focus:border-black"
                />
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-black hover:bg-gray-100"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="rounded-md bg-black px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
                >
                  {isSubmitting ? "Creating…" : "Create"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
