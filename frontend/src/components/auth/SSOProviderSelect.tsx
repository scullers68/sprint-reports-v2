/**
 * SSO Provider Selection Component
 * 
 * Displays available SSO providers and handles authentication initiation.
 */

import React, { useEffect, useState } from 'react';

interface SSOProvider {
  type: string;
  name: string;
  initiate_url: string;
  callback_url: string;
  client_id?: string;
  tenant_id?: string;
  entity_id?: string;
}

interface SSOConfig {
  sso_enabled: boolean;
  auto_provision_users: boolean;
  allowed_domains: string[];
  providers: SSOProvider[];
}

interface SSOProviderSelectProps {
  onProviderSelect?: (provider: SSOProvider) => void;
  className?: string;
}

export const SSOProviderSelect: React.FC<SSOProviderSelectProps> = ({
  onProviderSelect,
  className = ''
}) => {
  const [config, setConfig] = useState<SSOConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSSOConfig();
  }, []);

  const fetchSSOConfig = async () => {
    try {
      const response = await fetch('/api/v1/auth/sso/config');
      
      if (!response.ok) {
        if (response.status === 404) {
          setError('SSO authentication is not enabled');
        } else {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return;
      }

      const data = await response.json();
      setConfig(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load SSO configuration');
    } finally {
      setLoading(false);
    }
  };

  const initiateSSO = async (provider: SSOProvider) => {
    try {
      const response = await fetch(provider.initiate_url);
      
      if (!response.ok) {
        throw new Error(`Failed to initiate SSO: ${response.statusText}`);
      }

      const data = await response.json();
      
      // Redirect to the provider's authentication URL
      if (data.auth_url) {
        window.location.href = data.auth_url;
      }

      // Call the callback if provided
      if (onProviderSelect) {
        onProviderSelect(provider);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to initiate SSO');
    }
  };

  const getProviderIcon = (type: string): string => {
    switch (type) {
      case 'google':
        return '🔍'; // Google icon placeholder
      case 'azure':
        return '🟦'; // Microsoft icon placeholder
      case 'saml':
        return '🔐'; // SAML icon placeholder
      default:
        return '🔗'; // Generic icon placeholder
    }
  };

  const getProviderStyles = (type: string): string => {
    const baseStyles = 'flex items-center px-4 py-3 border rounded-lg hover:bg-gray-50 transition-colors cursor-pointer';
    
    switch (type) {
      case 'google':
        return `${baseStyles} border-red-300 hover:border-red-400`;
      case 'azure':
        return `${baseStyles} border-blue-300 hover:border-blue-400`;
      case 'saml':
        return `${baseStyles} border-green-300 hover:border-green-400`;
      default:
        return `${baseStyles} border-gray-300 hover:border-gray-400`;
    }
  };

  if (loading) {
    return (
      <div className={`flex justify-center items-center p-8 ${className}`}>
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-2 text-gray-600">Loading SSO providers...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`p-4 bg-red-50 border border-red-200 rounded-lg ${className}`}>
        <div className="flex items-center">
          <span className="text-red-500 text-xl mr-2">⚠️</span>
          <div>
            <h3 className="text-red-800 font-medium">SSO Configuration Error</h3>
            <p className="text-red-600 text-sm mt-1">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  if (!config || !config.sso_enabled || config.providers.length === 0) {
    return (
      <div className={`p-4 bg-yellow-50 border border-yellow-200 rounded-lg ${className}`}>
        <div className="flex items-center">
          <span className="text-yellow-500 text-xl mr-2">ℹ️</span>
          <div>
            <h3 className="text-yellow-800 font-medium">SSO Not Available</h3>
            <p className="text-yellow-600 text-sm mt-1">
              No SSO providers are currently configured. Please contact your administrator.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`space-y-3 ${className}`}>
      <div className="text-center mb-4">
        <h3 className="text-lg font-medium text-gray-900">Sign in with SSO</h3>
        <p className="text-sm text-gray-600 mt-1">
          Choose your organization's authentication provider
        </p>
      </div>

      {config.providers.map((provider) => (
        <button
          key={provider.type}
          onClick={() => initiateSSO(provider)}
          className={getProviderStyles(provider.type)}
          type="button"
        >
          <span className="text-2xl mr-3">{getProviderIcon(provider.type)}</span>
          <div className="flex-1 text-left">
            <div className="font-medium text-gray-900">{provider.name}</div>
            <div className="text-sm text-gray-500">
              {provider.type === 'google' && 'Sign in with your Google account'}
              {provider.type === 'azure' && 'Sign in with Microsoft Azure AD'}
              {provider.type === 'saml' && 'Sign in with SAML SSO'}
              {provider.type === 'oauth' && 'Sign in with OAuth 2.0'}
            </div>
          </div>
          <span className="text-gray-400">→</span>
        </button>
      ))}

      {config.allowed_domains.length > 0 && (
        <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="flex items-start">
            <span className="text-blue-500 text-sm mr-2">ℹ️</span>
            <div>
              <p className="text-blue-800 text-sm font-medium">Domain Restrictions</p>
              <p className="text-blue-600 text-xs mt-1">
                Only users from the following domains can sign in: {config.allowed_domains.join(', ')}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SSOProviderSelect;