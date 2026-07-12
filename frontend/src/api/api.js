import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Attach the JWT (if present) to every outgoing request. Reading straight from
// localStorage per-request (rather than caching it in a closure) means a fresh
// login in another tab, or a manual logout, is picked up on the very next call.
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("assetflow_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// A 401 from any endpoint means the token is missing/expired/invalid — clear it
// and force back to login rather than leaving the app in a half-authenticated
// state making requests that will keep failing the same way.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("assetflow_token");
      localStorage.removeItem("assetflow_user");
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

export default api;
