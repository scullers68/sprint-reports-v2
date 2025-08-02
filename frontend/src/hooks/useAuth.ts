'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api';
import { User, LoginRequest, AuthResponse } from '@/types/api';

export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

export interface AuthActions {
  login: (credentials: LoginRequest) => Promise<void>;
  logout: () => Promise<void>;
  clearError: () => void;
  checkAuth: () => Promise<void>;
}

export function useAuth(): AuthState & AuthActions {
  const [state, setState] = useState<AuthState>({
    user: null,
    isAuthenticated: false,
    isLoading: true,
    error: null,
  });

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      setState(prev => ({ ...prev, isLoading: true, error: null }));
      
      // Check if user is authenticated using existing TokenManager
      if (apiClient.isAuthenticated()) {
        // Try to get user info from localStorage first
        const storedUser = typeof window !== 'undefined' 
          ? localStorage.getItem('user') 
          : null;
        
        if (storedUser) {
          const user = JSON.parse(storedUser);
          setState(prev => ({
            ...prev,
            user,
            isAuthenticated: true,
            isLoading: false,
          }));
        } else {
          // Fetch current user from API
          const user = await apiClient.getCurrentUser();
          setState(prev => ({
            ...prev,
            user,
            isAuthenticated: true,
            isLoading: false,
          }));
        }
      } else {
        setState(prev => ({
          ...prev,
          user: null,
          isAuthenticated: false,
          isLoading: false,
        }));
      }
    } catch (error: any) {
      console.warn('Auth check failed:', error);
      // Clear invalid tokens
      apiClient.clearAuth();
      setState(prev => ({
        ...prev,
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: error.message || 'Authentication check failed',
      }));
    }
  };

  const login = async (credentials: LoginRequest) => {
    try {
      setState(prev => ({ ...prev, isLoading: true, error: null }));
      
      // Use existing API client login method
      const response: AuthResponse = await apiClient.login(credentials);
      
      setState(prev => ({
        ...prev,
        user: response.user,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      }));
    } catch (error: any) {
      setState(prev => ({
        ...prev,
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: error.message || 'Login failed',
      }));
      throw error;
    }
  };

  const logout = async () => {
    try {
      setState(prev => ({ ...prev, isLoading: true, error: null }));
      
      // Use existing API client logout method
      await apiClient.logout();
      
      setState(prev => ({
        ...prev,
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: null,
      }));
    } catch (error: any) {
      console.warn('Logout API call failed:', error);
      // Clear tokens even if API call fails
      apiClient.clearAuth();
      setState(prev => ({
        ...prev,
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: null,
      }));
    }
  };

  const clearError = () => {
    setState(prev => ({ ...prev, error: null }));
  };

  return {
    ...state,
    login,
    logout,
    clearError,
    checkAuth,
  };
}