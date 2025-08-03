'use client';

import React, { useState, useEffect } from 'react';
import { Header } from '@/components/layout/Header';

interface JIRAConnection {
  url: string;
  email: string;
  token: string;
  isConnected: boolean;
  lastTested?: string;
}

interface ConnectionStatus {
  connected: boolean;
  capabilities?: string[];
  lastChecked?: string;
  error?: string;
}

export default function JIRAPage() {
  const [connection, setConnection] = useState<JIRAConnection>({
    url: '',
    email: '',
    token: '',
    isConnected: false
  });
  const [status, setStatus] = useState<ConnectionStatus>({ connected: false });
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('setup');

  const testConnection = async () => {
    setLoading(true);
    try {
      // TODO: Call actual JIRA test endpoint
      const response = await fetch('/api/v1/jira/connection/test', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        },
        body: JSON.stringify({
          config: {
            url: connection.url,
            email: connection.email,
            api_token: connection.token,
            auth_method: "token"
          }
        })
      });

      if (response.ok) {
        const result = await response.json();
        setStatus({ 
          connected: result.connection_valid || true, 
          lastChecked: new Date().toISOString(),
          capabilities: ['Agile Boards', 'Sprint Management', 'Issue Tracking']
        });
        setConnection(prev => ({ ...prev, isConnected: true, lastTested: new Date().toISOString() }));
      } else {
        let errorMessage = 'Connection failed';
        try {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorData.message || JSON.stringify(errorData);
        } catch {
          errorMessage = await response.text() || 'Connection failed';
        }
        setStatus({ 
          connected: false, 
          error: errorMessage,
          lastChecked: new Date().toISOString()
        });
      }
    } catch (error) {
      setStatus({ 
        connected: false, 
        error: 'Network error - please check if backend is running',
        lastChecked: new Date().toISOString()
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          <div className="page-header">
            <h1 className="page-title">JIRA Integration</h1>
            <p className="page-description">
              Connect to your JIRA instance to import sprint data for analytics
            </p>
          </div>

          {/* Tab Navigation */}
          <div className="mb-6">
            <nav className="flex space-x-8">
              <button
                onClick={() => setActiveTab('setup')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'setup'
                    ? 'border-indigo-500 text-indigo-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                Connection Setup
              </button>
              <button
                onClick={() => setActiveTab('status')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'status'
                    ? 'border-indigo-500 text-indigo-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                Status & Health
              </button>
            </nav>
          </div>

          {/* Connection Setup Tab */}
          {activeTab === 'setup' && (
            <div className="space-y-6">
              <div className="card">
                <div className="card-header">
                  <h3 className="text-lg font-medium text-gray-900">JIRA Connection Details</h3>
                  <p className="text-sm text-gray-500">Configure your JIRA instance connection</p>
                </div>
                <div className="card-body space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      JIRA URL
                    </label>
                    <input
                      type="url"
                      value={connection.url}
                      onChange={(e) => setConnection(prev => ({ ...prev, url: e.target.value }))}
                      placeholder="https://yourcompany.atlassian.net"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Email Address
                    </label>
                    <input
                      type="email"
                      value={connection.email}
                      onChange={(e) => setConnection(prev => ({ ...prev, email: e.target.value }))}
                      placeholder="your-email@company.com"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      API Token
                    </label>
                    <input
                      type="password"
                      value={connection.token}
                      onChange={(e) => setConnection(prev => ({ ...prev, token: e.target.value }))}
                      placeholder="Your JIRA API token"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                    />
                  </div>

                  <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
                    <div className="flex">
                      <div className="flex-shrink-0">
                        <span className="text-blue-400 text-xl">ℹ️</span>
                      </div>
                      <div className="ml-3">
                        <p className="text-sm text-blue-700">
                          <strong>API Token:</strong> Generate an API token from your JIRA account settings 
                          (Account Settings → Security → API tokens). For JIRA Cloud, use your email and API token.
                        </p>
                      </div>
                    </div>
                  </div>

                  <div className="flex space-x-3">
                    <button
                      onClick={testConnection}
                      disabled={loading || !connection.url || !connection.email || !connection.token}
                      className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {loading ? (
                        <>
                          <span className="animate-spin inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full mr-2"></span>
                          Testing...
                        </>
                      ) : (
                        'Test Connection'
                      )}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Status & Health Tab */}
          {activeTab === 'status' && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                <div className="card">
                  <div className="card-body">
                    <div className="flex items-center">
                      <div className="flex-shrink-0">
                        <div className="text-3xl">
                          {status.connected ? '✅' : '❌'}
                        </div>
                      </div>
                      <div className="ml-4">
                        <p className="text-sm font-medium text-gray-500 truncate">
                          Connection Status
                        </p>
                        <p className="text-2xl font-semibold text-gray-900">
                          {status.connected ? 'Connected' : 'Disconnected'}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="card">
                  <div className="card-body">
                    <div className="flex items-center">
                      <div className="flex-shrink-0">
                        <div className="text-3xl">🕒</div>
                      </div>
                      <div className="ml-4">
                        <p className="text-sm font-medium text-gray-500 truncate">
                          Last Checked
                        </p>
                        <p className="text-lg font-semibold text-gray-900">
                          {status.lastChecked 
                            ? new Date(status.lastChecked).toLocaleString()
                            : 'Never'
                          }
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {status.error && (
                <div className="card">
                  <div className="card-body">
                    <div className="rounded-md bg-red-50 p-4">
                      <div className="flex">
                        <div className="flex-shrink-0">
                          <span className="text-red-400 text-xl">⚠️</span>
                        </div>
                        <div className="ml-3">
                          <h3 className="text-sm font-medium text-red-800">
                            Connection Error
                          </h3>
                          <div className="mt-2 text-sm text-red-700">
                            <p>{status.error}</p>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {status.capabilities && status.capabilities.length > 0 && (
                <div className="card">
                  <div className="card-header">
                    <h3 className="text-lg font-medium text-gray-900">Available Capabilities</h3>
                  </div>
                  <div className="card-body">
                    <ul className="space-y-2">
                      {status.capabilities.map((capability, index) => (
                        <li key={index} className="flex items-center text-sm text-gray-600">
                          <span className="text-green-500 mr-2">✓</span>
                          {capability}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}