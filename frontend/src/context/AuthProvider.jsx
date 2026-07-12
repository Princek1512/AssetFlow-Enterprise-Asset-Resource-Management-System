import { createContext, useContext, useState, useEffect } from "react";
import api from "../api/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    const token = localStorage.getItem("access_token");
    if (token) {
      api.defaults.headers.common["Authorization"] = `Bearer ${token}`;
      try {
        const { data } = await api.get("/auth/me");
        setUser(data);
      } catch (err) {
        localStorage.removeItem("access_token");
        delete api.defaults.headers.common["Authorization"];
      }
    }
    setIsLoading(false);
  };

  const login = async (email, password) => {
    setIsLoading(true);
    try {
      const formData = new URLSearchParams();
      formData.append("username", email);
      formData.append("password", password);
      const { data } = await api.post("/auth/login", formData, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });
      localStorage.setItem("access_token", data.access_token);
      await checkAuth();
      return { success: true };
    } catch (err) {
      setIsLoading(false);
      return { success: false, error: err.response?.data?.detail || "Login failed" };
    }
  };

  const googleLogin = async (credential) => {
    setIsLoading(true);
    try {
      const { data } = await api.post("/auth/google-login", { token: credential });
      localStorage.setItem("access_token", data.access_token);
      await checkAuth();
      return { success: true };
    } catch (err) {
      setIsLoading(false);
      return { success: false, error: err.response?.data?.detail || "Google Login failed" };
    }
  };

  const signup = async (fullName, email, password) => {
    setIsLoading(true);
    try {
      await api.post("/auth/signup", { full_name: fullName, email, password });
      return await login(email, password);
    } catch (err) {
      setIsLoading(false);
      return { success: false, error: err.response?.data?.detail || "Signup failed" };
    }
  };

  const logout = () => {
    localStorage.removeItem("access_token");
    delete api.defaults.headers.common["Authorization"];
    setUser(null);
  };

  const hasRole = (...roles) => {
    if (!user) return false;
    return roles.includes(user.role);
  };

  return (
    <AuthContext.Provider
      value={{ user, isAuthenticated: !!user, isLoading, login, googleLogin, signup, logout, hasRole }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);