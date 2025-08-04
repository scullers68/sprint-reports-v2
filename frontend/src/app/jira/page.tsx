'use client';

import React, { useState, useEffect } from 'react';
import { Header } from '@/components/layout/Header';
import { apiClient } from '@/lib/api';
import { useAuthContext } from '@/contexts/AuthContext';

interface ConnectionStatus {
  connected: boolean;
  lastChecked?: string;
  error?: string;
}

interface CacheStatus {
  total_sprints: number;
  active_sprints: number;
  future_sprints: number;
  closed_sprints: number;
  oldest_fetch?: string;
  newest_fetch?: string;
}

interface Sprint {
  id: number;
  name: string;
  state: string;
  goal?: string;
  startDate?: string;
  endDate?: string;
  board: {
    id: number;
    name: string;
    type: string;
    projectKey?: string;
  };
}

export default function JIRAIntegrationPage() {
  const { user, isAuthenticated, isLoading } = useAuthContext();
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>({ connected: false });
  const [cacheStatus, setCacheStatus] = useState<CacheStatus | null>(null);
  const [sprints, setSprints] = useState<Sprint[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Redirect if not authenticated
  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      window.location.href = '/login';
    }
  }, [isAuthenticated, isLoading]);

  // Load initial data
  useEffect(() => {
    if (isAuthenticated) {
      loadConnectionStatus();
      loadCacheStatus();
      loadSprints();
    }
  }, [isAuthenticated]);

  // Auto-refresh data every 30 seconds
  useEffect(() => {
    if (isAuthenticated) {
      const interval = setInterval(() => {
        loadCacheStatus();
        loadSprints();
      }, 30000);
      return () => clearInterval(interval);
    }
  }, [isAuthenticated]);

  // Clear messages after 5 seconds
  useEffect(() => {
    if (message) {
      const timer = setTimeout(() => setMessage(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [message]);

  const loadConnectionStatus = async () => {
    try {
      // Use the public health endpoint directly without authentication
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001'}/health`);
      if (response.ok) {
        setConnectionStatus({
          connected: true,
          lastChecked: new Date().toISOString()
        });
      } else {
        throw new Error(`HTTP ${response.status}`);
      }
    } catch (error: any) {
      setConnectionStatus({
        connected: false,
        error: 'Backend not responding',
        lastChecked: new Date().toISOString()
      });
    }
  };

  const loadCacheStatus = async () => {
    try {
      const status = await apiClient.get('/jira/sprints/cache/status');
      setCacheStatus(status.cache);
    } catch (error: any) {
      console.error('Failed to load cache status:', error);
      // If authentication fails, set empty cache status to avoid errors
      setCacheStatus({
        total_sprints: 0,
        active_sprints: 0,
        future_sprints: 0,
        closed_sprints: 0
      });
    }
  };

  const loadSprints = async () => {
    setLoading(true);
    try {
      // Try direct call first to test
      console.log('Making API call to search sprints...');
      const sprintList = await apiClient.searchJiraSprints({
        limit: 50
      });
      console.log('Raw sprint data:', sprintList);
      console.log('Sprint count:', sprintList.length);
      
      // Filter to only show active and future sprints
      const filteredSprints = sprintList.filter((sprint: Sprint) => 
        sprint.state === 'active' || sprint.state === 'future'
      );
      console.log('Filtered sprints (active/future):', filteredSprints.length);
      console.log('Filtered sprint states:', filteredSprints.map(s => s.state));
      
      // Sort: active first, then future, then by name
      const sortedSprints = filteredSprints.sort((a: Sprint, b: Sprint) => {
        if (a.state === 'active' && b.state !== 'active') return -1;
        if (a.state !== 'active' && b.state === 'active') return 1;
        return a.name.localeCompare(b.name);
      });
      setSprints(sortedSprints);
    } catch (error: any) {
      console.error('Failed to load sprints:', error);
      console.error('Error details:', error.message, error.status);
      if (error.message && error.message.includes('Authentication required')) {
        setMessage({ type: 'error', text: 'Please log in to access sprint data' });
      } else {
        setMessage({ type: 'error', text: `Failed to load sprints: ${error.message || 'Unknown error'}` });
      }
      setSprints([]);
    } finally {
      setLoading(false);
    }
  };

  const refreshCache = async () => {
    setLoading(true);
    try {
      const result = await apiClient.post('/jira/sprints/cache/refresh', {});
      setMessage({ type: 'success', text: 'Sprint cache refreshed successfully' });
      await loadCacheStatus();
      await loadSprints();
    } catch (error: any) {
      console.error('Failed to refresh cache:', error);
      setMessage({ type: 'error', text: 'Failed to refresh sprint cache' });
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    loadSprints();
  };

  if (isLoading) {
    return <div className="flex items-center justify-center min-h-screen">Loading...</div>;
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Sprint Analytics</h1>
          <p className="mt-2 text-gray-600">
            Real-time active and future sprint data from JIRA • Auto-refreshed every 2 hours
          </p>
        </div>

        {/* Message */}
        {message && (
          <div className={`mb-6 p-4 rounded-md ${
            message.type === 'success' ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'
          }`}>
            {message.text}
          </div>
        )}

        {/* Connection Status */}
        <div className="bg-white shadow rounded-lg p-6 mb-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Connection Status</h2>
          <div className="flex items-center space-x-4">
            <div className="flex items-center">
              <div className={`w-3 h-3 rounded-full mr-2 ${
                connectionStatus.connected ? 'bg-green-400' : 'bg-red-400'
              }`} />
              <span className={connectionStatus.connected ? 'text-green-800' : 'text-red-800'}>
                {connectionStatus.connected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
            {connectionStatus.lastChecked && (
              <span className="text-sm text-gray-500">
                Last checked: {new Date(connectionStatus.lastChecked).toLocaleString()}
              </span>
            )}
          </div>
          {connectionStatus.error && (
            <p className="mt-2 text-sm text-red-600">{connectionStatus.error}</p>
          )}
        </div>

        {/* Cache Status */}
        {cacheStatus && (
          <div className="bg-white shadow rounded-lg p-6 mb-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-medium text-gray-900">Sprint Cache</h2>
              <button
                onClick={refreshCache}
                disabled={loading}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
              >
                {loading ? 'Refreshing...' : 'Refresh Cache'}
              </button>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-900">{cacheStatus.total_sprints}</div>
                <div className="text-sm text-gray-500">Total Sprints</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">{cacheStatus.active_sprints}</div>
                <div className="text-sm text-gray-500">Active</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">{cacheStatus.future_sprints}</div>
                <div className="text-sm text-gray-500">Future</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-600">{cacheStatus.closed_sprints}</div>
                <div className="text-sm text-gray-500">Closed</div>
              </div>
            </div>
            {cacheStatus.newest_fetch && (
              <p className="mt-4 text-sm text-gray-500">
                Last updated: {new Date(cacheStatus.newest_fetch).toLocaleString()}
              </p>
            )}
          </div>
        )}

        {/* Active & Future Sprints */}
        <div className="bg-white shadow rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-medium text-gray-900">Active & Future Sprints</h2>
            <div className="flex items-center space-x-2">
              <span className="text-sm text-gray-500">Auto-refreshes every 30s</span>
              <button
                onClick={loadSprints}
                disabled={loading}
                className="px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 disabled:opacity-50"
              >
                {loading ? 'Loading...' : 'Refresh'}
              </button>
            </div>
          </div>
          
          {/* Search Form */}
          <form onSubmit={handleSearch} className="mb-6">
            <div className="flex">
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Filter sprints by name, board, or project..."
                className="flex-1 px-3 py-2 border border-gray-300 rounded-l-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
              <button
                type="submit"
                disabled={loading}
                className="px-4 py-2 bg-blue-600 text-white rounded-r-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
              >
                {loading ? 'Filtering...' : 'Filter'}
              </button>
            </div>
          </form>

          {/* Active Sprints Section */}
          {sprints.filter(s => s.state === 'active').length > 0 && (
            <div className="mb-6">
              <h3 className="text-md font-semibold text-gray-900 mb-3 flex items-center">
                <span className="w-2 h-2 bg-green-500 rounded-full mr-2"></span>
                Active Sprints ({sprints.filter(s => s.state === 'active').length})
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {sprints.filter(s => s.state === 'active').map((sprint) => (
                  <div
                    key={sprint.id}
                    className="p-4 border-2 border-green-200 bg-green-50 rounded-lg hover:border-green-300 transition-colors"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <h4 className="text-sm font-semibold text-gray-900">
                          {sprint.name}
                        </h4>
                        <p className="text-xs text-gray-600 mt-1">
                          <span className="font-medium">{sprint.board?.name}</span>
                          {sprint.board?.projectKey && (
                            <span className="ml-2 text-gray-500">• {sprint.board.projectKey}</span>
                          )}
                        </p>
                        {sprint.goal && (
                          <p className="text-xs text-gray-700 mt-2 italic">
                            Goal: {sprint.goal}
                          </p>
                        )}
                        {(sprint.startDate || sprint.endDate) && (
                          <div className="flex items-center mt-2 text-xs text-gray-600">
                            <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                            </svg>
                            <span>
                              {sprint.startDate && new Date(sprint.startDate).toLocaleDateString()}
                              {sprint.endDate && ` → ${new Date(sprint.endDate).toLocaleDateString()}`}
                            </span>
                          </div>
                        )}
                        <div className="mt-2">
                          <span className="text-xs text-gray-500">Sprint ID: {sprint.id}</span>
                        </div>
                      </div>
                      <div className="ml-3 flex-shrink-0">
                        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                          Active
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Future Sprints Section */}
          {sprints.filter(s => s.state === 'future').length > 0 && (
            <div className="mb-6">
              <h3 className="text-md font-semibold text-gray-900 mb-3 flex items-center">
                <span className="w-2 h-2 bg-blue-500 rounded-full mr-2"></span>
                Future Sprints ({sprints.filter(s => s.state === 'future').length})
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {sprints.filter(s => s.state === 'future').map((sprint) => (
                  <div
                    key={sprint.id}
                    className="p-4 border border-blue-200 bg-blue-50 rounded-lg hover:border-blue-300 transition-colors"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <h4 className="text-sm font-semibold text-gray-900">
                          {sprint.name}
                        </h4>
                        <p className="text-xs text-gray-600 mt-1">
                          <span className="font-medium">{sprint.board?.name}</span>
                          {sprint.board?.projectKey && (
                            <span className="ml-2 text-gray-500">• {sprint.board.projectKey}</span>
                          )}
                        </p>
                        {sprint.goal && (
                          <p className="text-xs text-gray-700 mt-2 italic">
                            Goal: {sprint.goal}
                          </p>
                        )}
                        {(sprint.startDate || sprint.endDate) && (
                          <div className="flex items-center mt-2 text-xs text-gray-600">
                            <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 002 2z" />
                            </svg>
                            <span>
                              {sprint.startDate && `Start: ${new Date(sprint.startDate).toLocaleDateString()}`}
                              {sprint.endDate && ` → End: ${new Date(sprint.endDate).toLocaleDateString()}`}
                            </span>
                          </div>
                        )}
                        <div className="mt-2">
                          <span className="text-xs text-gray-500">Sprint ID: {sprint.id}</span>
                        </div>
                      </div>
                      <div className="ml-3 flex-shrink-0">
                        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                          Future
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* No sprints message */}
          {sprints.length === 0 && !loading && (
            <div className="text-center py-8 text-gray-500">
              No active or future sprints found. Try searching or refresh the cache.
            </div>
          )}

          {/* Loading message */}
          {loading && (
            <div className="text-center py-8 text-gray-500">
              Loading sprints...
            </div>
          )}
        </div>
      </div>
    </div>
  );
}