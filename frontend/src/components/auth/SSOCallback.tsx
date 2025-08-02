/**
 * SSO Callback Handler Component
 * 
 * Handles OAuth callbacks from SSO providers and completes authentication flow.
 */

'use client';

import React, { useEffect, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';

interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: {
    id: number;
    email: string;
    full_name: string;
    username: string;
    is_active: boolean;
    role: string;
    sso_provider: string;
  };
}

interface SSOCallbackProps {
  provider: 'google' | 'azure' | 'oauth' | 'saml';
  onAuthSuccess?: (response: AuthResponse) => void;
  onAuthError?: (error: string) => void;
  redirectTo?: string;
}

export const SSOCallback: React.FC<SSOCallbackProps> = ({
  provider,
  onAuthSuccess,
  onAuthError,
  redirectTo = '/dashboard'
}) => {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [status, setStatus] = useState<'processing' | 'success' | 'error'>('processing');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    handleCallback();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleCallback = async () => {
    try {
      // Extract callback parameters
      const code = searchParams.get('code');
      const state = searchParams.get('state');
      const errorParam = searchParams.get('error');
      const errorDescription = searchParams.get('error_description');

      // Handle OAuth errors
      if (errorParam) {
        const errorMessage = errorDescription || `OAuth error: ${errorParam}`;
        handleError(errorMessage);
        return;
      }

      // Validate required parameters
      if (!code || !state) {
        handleError('Missing required OAuth parameters (code or state)');
        return;
      }

      // Build callback URL based on provider
      const callbackUrl = getCallbackUrl(provider);
      
      // Make callback request to backend
      const response = await fetch(`${callbackUrl}?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}`);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
      }

      const authData: AuthResponse = await response.json();

      // Store authentication token
      localStorage.setItem('access_token', authData.access_token);
      localStorage.setItem('token_type', authData.token_type);
      localStorage.setItem('user', JSON.stringify(authData.user));

      // Set expiration time
      const expiresAt = Date.now() + (authData.expires_in * 1000);
      localStorage.setItem('token_expires_at', expiresAt.toString());

      setStatus('success');

      // Call success callback
      if (onAuthSuccess) {
        onAuthSuccess(authData);
      }

      // Redirect after successful authentication
      setTimeout(() => {
        router.push(redirectTo);
      }, 2000);

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Authentication failed';
      handleError(errorMessage);
    }
  };

  const handleError = (errorMessage: string) => {
    setStatus('error');
    setError(errorMessage);

    if (onAuthError) {
      onAuthError(errorMessage);
    }

    // Redirect to login page after error
    setTimeout(() => {
      router.push('/login');
    }, 5000);
  };

  const getCallbackUrl = (provider: string): string => {
    const baseUrl = '/api/v1/auth/sso';
    
    switch (provider) {
      case 'google':
        return `${baseUrl}/google/callback`;
      case 'azure':
        return `${baseUrl}/azure/callback`;
      case 'saml':
        return `${baseUrl}/saml/acs`;
      case 'oauth':
      default:
        return `${baseUrl}/oauth/callback`;
    }
  };

  const getProviderName = (provider: string): string => {
    switch (provider) {
      case 'google':
        return 'Google';
      case 'azure':
        return 'Microsoft Azure AD';
      case 'saml':
        return 'SAML SSO';
      case 'oauth':
      default:
        return 'OAuth 2.0';
    }
  };

  const renderStatus = () => {
    switch (status) {
      case 'processing':
        return (
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">
              Completing Authentication
            </h2>
            <p className="text-gray-600">
              Processing {getProviderName(provider)} authentication...
            </p>
          </div>
        );

      case 'success':
        return (
          <div className="text-center">
            <div className="text-green-500 text-6xl mb-4">✓</div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">
              Authentication Successful
            </h2>
            <p className="text-gray-600 mb-4">
              You have been successfully authenticated with {getProviderName(provider)}.
            </p>
            <p className="text-sm text-gray-500">
              Redirecting to dashboard...
            </p>
          </div>
        );

      case 'error':
        return (
          <div className="text-center">
            <div className="text-red-500 text-6xl mb-4">✗</div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">
              Authentication Failed
            </h2>
            <p className="text-gray-600 mb-4">
              There was an error completing authentication with {getProviderName(provider)}.
            </p>
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
              <p className="text-red-800 text-sm">{error}</p>
            </div>
            <p className="text-sm text-gray-500">
              Redirecting to login page...
            </p>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div className="bg-white shadow-lg rounded-lg p-8">
          {renderStatus()}
        </div>
      </div>
    </div>
  );
};

export default SSOCallback;