import * as React from 'react';
import {
  api,
  type UserProfileResponse,
  getStoredAuthToken,
  setStoredAuthToken,
  setStoredUserIdentifier,
} from '@/services/api';

interface AuthContextValue {
  user: UserProfileResponse | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => void;
  refetchUser: () => Promise<void>;
}

const AuthContext = React.createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = React.useState<string | null>(() => getStoredAuthToken());
  const [user, setUser] = React.useState<UserProfileResponse | null>(null);
  const [isLoading, setIsLoading] = React.useState<boolean>(true);

  const fetchProfile = React.useCallback(async (activeToken?: string | null) => {
    const currentToken = activeToken !== undefined ? activeToken : getStoredAuthToken();
    if (!currentToken) {
      setUser(null);
      setIsLoading(false);
      return;
    }

    try {
      const profile = await api.getCurrentUser();
      setUser(profile);
      setStoredUserIdentifier(profile.email);
    } catch {
      // If token is invalid or expired, clear it
      setStoredAuthToken(null);
      setToken(null);
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  React.useEffect(() => {
    fetchProfile(token);
  }, [fetchProfile, token]);

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const res = await api.loginUser({ email, password });
      setToken(res.access_token);
      setUser(res.user);
      setStoredAuthToken(res.access_token);
      setStoredUserIdentifier(res.user.email);
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (email: string, password: string, fullName?: string) => {
    setIsLoading(true);
    try {
      const res = await api.registerUser({ email, password, full_name: fullName });
      setToken(res.access_token);
      setUser(res.user);
      setStoredAuthToken(res.access_token);
      setStoredUserIdentifier(res.user.email);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    setStoredAuthToken(null);
    setToken(null);
    setUser(null);
    setStoredUserIdentifier('default');
  };

  const refetchUser = async () => {
    await fetchProfile(token);
  };

  const value: AuthContextValue = {
    user,
    token,
    isAuthenticated: !!user && !!token,
    isLoading,
    login,
    register,
    logout,
    refetchUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = React.useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

