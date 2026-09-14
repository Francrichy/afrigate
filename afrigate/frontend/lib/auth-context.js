import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { api, getToken, setToken } from "./api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [authModalOpen, setAuthModalOpen] = useState(false);

  const refreshWallet = useCallback(async () => {
    if (!getToken()) return;
    try {
      const wallet = await api.getWallet();
      setUser((prev) => (prev ? { ...prev, credit_balance: wallet.credit_balance } : prev));
    } catch (e) {
      // token likely expired
      setToken(null);
      setUser(null);
    }
  }, []);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      setLoading(false);
      return;
    }
    api
      .getWallet()
      .then((wallet) => setUser({ credit_balance: wallet.credit_balance }))
      .catch(() => setToken(null))
      .finally(() => setLoading(false));
  }, []);

  function login(authResponse) {
    setToken(authResponse.access_token);
    setUser({ email: authResponse.email, credit_balance: authResponse.credit_balance });
    setAuthModalOpen(false);
  }

  function logout() {
    setToken(null);
    setUser(null);
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        loading,
        login,
        logout,
        refreshWallet,
        authModalOpen,
        setAuthModalOpen,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
