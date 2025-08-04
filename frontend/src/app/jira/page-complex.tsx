'use client';

import React, { useState, useEffect } from 'react';
import { Header } from '@/components/layout/Header';
import { apiClient } from '@/lib/api';
import { useAuthContext } from '@/contexts/AuthContext';

interface JIRAConnection {
  url: string;
  email: string;
  token: string;
  isConnected: boolean;
  lastTested?: string;
  name?: string;
  description?: string;
}

interface JIRAConfiguration {
  id: number;
  name: string;
  description?: string;
  url: string;
  email: string;
  auth_method: string;
  instance_type: string;
  environment: string;
  is_active: boolean;
  status: string;
  created_at: string;
  updated_at?: string;
  last_tested_at?: string;
  has_api_token: boolean;
  has_password: boolean;
}

interface ConnectionStatus {
  connected: boolean;
  capabilities?: string[];
  lastChecked?: string;
  error?: string;
}

interface JIRAProject {
  id: string;
  key: string;
  name: string;
  projectTypeKey: string;
  description?: string;
  board_count: number;
  permissions: {
    browse: boolean;
    administrate: boolean;
    create_issues: boolean;
  };
}

interface JIRABoard {
  id: number;
  name: string;
  type: string;
  project_key: string;
  configuration: {
    type: string;
    is_scrum: boolean;
    is_kanban: boolean;
    supports_sprints: boolean;
  };
  permissions: {
    view: boolean;
    edit: boolean;
    admin: boolean;
  };
  sprint_count: number;
  active_sprint?: {
    id: number;
    name: string;
    goal?: string;
    startDate?: string;
    endDate?: string;
  };
}

export default function JIRAPage() {
  const { user, isAuthenticated, isLoading } = useAuthContext();
  const [connection, setConnection] = useState<JIRAConnection>({
    url: '',
    email: '',
    token: '',
    isConnected: false,
    name: '',
    description: ''
  });
  const [status, setStatus] = useState<ConnectionStatus>({ connected: false });
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('configurations');
  
  // Configuration management state
  const [configurations, setConfigurations] = useState<JIRAConfiguration[]>([]);
  const [selectedConfigId, setSelectedConfigId] = useState<number | null>(null);
  const [configLoading, setConfigLoading] = useState(false);
  const [saveMessage, setSaveMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  
  // Project and board discovery state
  const [projects, setProjects] = useState<JIRAProject[]>([]);
  const [selectedProject, setSelectedProject] = useState<JIRAProject | null>(null);
  const [boards, setBoards] = useState<JIRABoard[]>([]);
  const [selectedBoards, setSelectedBoards] = useState<number[]>([]);
  const [projectSearch, setProjectSearch] = useState('');
  const [boardTypeFilter, setBoardTypeFilter] = useState<string>('');
  const [discoveryLoading, setDiscoveryLoading] = useState(false);
  const [selectionResult, setSelectionResult] = useState<any>(null);

  // Load configurations on component mount
  useEffect(() => {
    loadConfigurations();
  }, []);

  // Clear save message after 5 seconds
  useEffect(() => {
    if (saveMessage) {
      const timer = setTimeout(() => setSaveMessage(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [saveMessage]);

  const loadConfigurations = async () => {
    setConfigLoading(true);
    try {
      const response = await apiClient.getJiraConfigurations({ limit: 50 });
      setConfigurations(response.configurations || []);
    } catch (error: any) {
      console.error('Failed to load configurations:', error);
      setSaveMessage({ type: 'error', text: 'Failed to load saved configurations' });
    } finally {
      setConfigLoading(false);
    }
  };

  const loadConfiguration = async (configId: number) => {
    try {
      const config = await apiClient.getJiraConfiguration(configId, true); // Include sensitive fields for editing
      setConnection({
        url: config.url,
        email: config.email,
        token: config.api_token || '', // Load the actual token for editing
        isConnected: config.status === 'active',
        name: config.name,
        description: config.description,
        lastTested: config.last_tested_at
      });
      setSelectedConfigId(configId);
      setActiveTab('setup'); // Switch to setup tab to show loaded configuration
      setSaveMessage({ type: 'success', text: `Configuration "${config.name}" loaded successfully` });
    } catch (error: any) {
      console.error('Failed to load configuration:', error);
      setSaveMessage({ type: 'error', text: 'Failed to load configuration' });
    }
  };

  const saveConfiguration = async () => {
    if (!connection.name || !connection.url || !connection.email || !connection.token) {
      setSaveMessage({ type: 'error', text: 'Please fill in all required fields including configuration name' });
      return;
    }

    setLoading(true);
    try {
      const configData = {
        name: connection.name,
        description: connection.description || '',
        config: {
          url: connection.url,
          email: connection.email,
          api_token: connection.token,
          auth_method: 'token'
        },
        environment: 'production',
        test_connection: true
      };

      if (selectedConfigId) {
        // Update existing configuration
        await apiClient.updateJiraConfiguration(selectedConfigId, configData);
        setSaveMessage({ type: 'success', text: `Configuration "${connection.name}" updated successfully` });
      } else {
        // Create new configuration
        const newConfig = await apiClient.createJiraConfiguration(configData);
        setSelectedConfigId(newConfig.id);
        setSaveMessage({ type: 'success', text: `Configuration "${connection.name}" saved successfully` });
      }
      
      await loadConfigurations(); // Refresh the list
    } catch (error: any) {
      console.error('Failed to save configuration:', error);
      setSaveMessage({ 
        type: 'error', 
        text: error.message || 'Failed to save configuration' 
      });
    } finally {
      setLoading(false);
    }
  };

  const deleteConfiguration = async (configId: number, configName: string) => {
    if (!confirm(`Are you sure you want to delete the configuration "${configName}"?`)) {
      return;
    }

    try {
      await apiClient.deleteJiraConfiguration(configId);
      setSaveMessage({ type: 'success', text: `Configuration "${configName}" deleted successfully` });
      
      // Clear form if we deleted the currently selected config
      if (selectedConfigId === configId) {
        setConnection({
          url: '',
          email: '',
          token: '',
          isConnected: false,
          name: '',
          description: ''
        });
        setSelectedConfigId(null);
      }
      
      await loadConfigurations(); // Refresh the list
    } catch (error: any) {
      console.error('Failed to delete configuration:', error);
      setSaveMessage({ type: 'error', text: 'Failed to delete configuration' });
    }
  };

  const clearForm = () => {
    setConnection({
      url: '',
      email: '',
      token: '',
      isConnected: false,
      name: '',
      description: ''
    });
    setSelectedConfigId(null);
    setStatus({ connected: false });
    setSaveMessage(null);
  };

  const testConnection = async () => {
    setLoading(true);
    try {
      const result = await apiClient.testJiraConnection({
        url: connection.url,
        email: connection.email,
        api_token: connection.token,
        auth_method: "token"
      });

      setStatus({ 
        connected: result.connection_valid || true, 
        lastChecked: new Date().toISOString(),
        capabilities: result.tests?.projects?.success ? ['Projects', 'Boards', 'Sprints'] : []
      });
      setConnection(prev => ({ ...prev, isConnected: true, lastTested: new Date().toISOString() }));
      
      // If connection is successful, automatically load sprints
      if (result.connection_valid) {
        await loadSprints();
      }
    } catch (error: any) {
      console.error('Connection test failed:', error);
      setStatus({ 
        connected: false, 
        error: error.message || 'Connection failed',
        lastChecked: new Date().toISOString()
      });
    } finally {
      setLoading(false);
    }
  };

  const loadSprints = async () => {
    setDiscoveryLoading(true);
    try {
      const sprintList = await apiClient.searchJiraSprints({
        search: projectSearch || undefined,
        limit: 50
      });
      setProjects(sprintList); // Using projects state to store sprints for now
    } catch (error: any) {
      console.error('Failed to load sprints:', error);
    } finally {
      setDiscoveryLoading(false);
    }
  };

  const loadProjectBoards = async (projectKey: string) => {
    setDiscoveryLoading(true);
    try {
      const boardList = await apiClient.getJiraProjectBoards(projectKey, {
        board_type: boardTypeFilter || undefined
      });
      setBoards(boardList);
    } catch (error: any) {
      console.error('Failed to load boards:', error);
    } finally {
      setDiscoveryLoading(false);
    }
  };

  const selectProject = async (project: JIRAProject) => {
    setSelectedProject(project);
    setBoards([]);
    setSelectedBoards([]);
    await loadProjectBoards(project.key);
  };

  const toggleBoardSelection = (boardId: number) => {
    setSelectedBoards(prev => 
      prev.includes(boardId) 
        ? prev.filter(id => id !== boardId)
        : [...prev, boardId]
    );
  };

  const confirmSelection = async () => {
    if (!selectedProject || selectedBoards.length === 0) return;
    
    setLoading(true);
    try {
      const result = await apiClient.selectJiraProject(selectedProject.key, selectedBoards);
      setSelectionResult(result);
      setActiveTab('selection');
    } catch (error: any) {
      console.error('Failed to select project:', error);
    } finally {
      setLoading(false);
    }
  };

  // Show loading while authentication is being checked
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Authentication Required</h2>
          <p className="text-gray-600 mb-4">Please log in to access JIRA configurations.</p>
          <a 
            href="/login" 
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
          >
            Go to Login
          </a>
        </div>
      </div>
    );
  }

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
                onClick={() => setActiveTab('configurations')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'configurations'
                    ? 'border-indigo-500 text-indigo-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                Saved Configurations
              </button>
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
                onClick={() => setActiveTab('discovery')}
                disabled={!status.connected}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'discovery'
                    ? 'border-indigo-500 text-indigo-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                } ${!status.connected ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                Project Discovery
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
              {selectionResult && (
                <button
                  onClick={() => setActiveTab('selection')}
                  className={`py-2 px-1 border-b-2 font-medium text-sm ${
                    activeTab === 'selection'
                      ? 'border-indigo-500 text-indigo-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  Selection Result
                </button>
              )}
            </nav>
          </div>

          {/* Saved Configurations Tab */}
          {activeTab === 'configurations' && (
            <div className="space-y-6">
              <div className="card">
                <div className="card-header">
                  <h3 className="text-lg font-medium text-gray-900">Saved JIRA Configurations</h3>
                  <p className="text-sm text-gray-500">Manage your saved JIRA connection configurations</p>
                </div>
                <div className="card-body">
                  {configLoading ? (
                    <div className="text-center py-8">
                      <div className="inline-flex items-center">
                        <span className="animate-spin inline-block w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full mr-3"></span>
                        Loading configurations...
                      </div>
                    </div>
                  ) : configurations.length === 0 ? (
                    <div className="text-center py-8">
                      <p className="text-gray-500">No saved configurations found.</p>
                      <button
                        onClick={() => setActiveTab('setup')}
                        className="mt-3 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-indigo-600 bg-indigo-100 hover:bg-indigo-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                      >
                        Create your first configuration
                      </button>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {configurations.map((config) => (
                        <div
                          key={config.id}
                          className={`p-4 border rounded-lg transition-colors ${
                            selectedConfigId === config.id
                              ? 'border-indigo-500 bg-indigo-50'
                              : 'border-gray-200 hover:border-gray-300'
                          }`}
                        >
                          <div className="flex items-start justify-between">
                            <div className="flex-1">
                              <h4 className="text-sm font-medium text-gray-900">{config.name}</h4>
                              {config.description && (
                                <p className="text-xs text-gray-600 mt-1">{config.description}</p>
                              )}
                              <div className="flex items-center space-x-4 mt-2 text-xs text-gray-500">
                                <span>{config.url}</span>
                                <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                                  config.status === 'active' 
                                    ? 'bg-green-100 text-green-800' 
                                    : config.status === 'error'
                                    ? 'bg-red-100 text-red-800'
                                    : 'bg-gray-100 text-gray-800'
                                }`}>
                                  {config.status}
                                </span>
                                {config.last_tested_at && (
                                  <span>Last tested: {new Date(config.last_tested_at).toLocaleDateString()}</span>
                                )}
                              </div>
                            </div>
                            <div className="flex items-center space-x-2">
                              <button
                                onClick={() => loadConfiguration(config.id)}
                                className="text-indigo-600 hover:text-indigo-900 text-sm font-medium"
                              >
                                Load
                              </button>
                              <button
                                onClick={() => deleteConfiguration(config.id, config.name)}
                                className="text-red-600 hover:text-red-900 text-sm font-medium"
                              >
                                Delete
                              </button>
                            </div>
                          </div>
                        </div>
                      ))}
                      <div className="pt-4 border-t">
                        <button
                          onClick={() => setActiveTab('setup')}
                          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                        >
                          Create New Configuration
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Connection Setup Tab */}
          {activeTab === 'setup' && (
            <div className="space-y-6">
              {/* Save Message */}
              {saveMessage && (
                <div className={`p-4 rounded-md ${
                  saveMessage.type === 'success' 
                    ? 'bg-green-50 border border-green-200' 
                    : 'bg-red-50 border border-red-200'
                }`}>
                  <div className="flex">
                    <div className="flex-shrink-0">
                      <span className={`text-xl ${
                        saveMessage.type === 'success' ? 'text-green-400' : 'text-red-400'
                      }`}>
                        {saveMessage.type === 'success' ? '✅' : '❌'}
                      </span>
                    </div>
                    <div className="ml-3">
                      <p className={`text-sm ${
                        saveMessage.type === 'success' ? 'text-green-700' : 'text-red-700'
                      }`}>
                        {saveMessage.text}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              <div className="card">
                <div className="card-header">
                  <h3 className="text-lg font-medium text-gray-900">JIRA Connection Details</h3>
                  <p className="text-sm text-gray-500">Configure your JIRA instance connection</p>
                </div>
                <div className="card-body space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Configuration Name *
                      </label>
                      <input
                        type="text"
                        value={connection.name || ''}
                        onChange={(e) => setConnection(prev => ({ ...prev, name: e.target.value }))}
                        placeholder="e.g., Production JIRA"
                        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Description
                      </label>
                      <input
                        type="text"
                        value={connection.description || ''}
                        onChange={(e) => setConnection(prev => ({ ...prev, description: e.target.value }))}
                        placeholder="Optional description"
                        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                      />
                    </div>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      JIRA URL *
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
                      Email Address *
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
                      API Token *
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

                  <div className="flex flex-wrap gap-3">
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
                    
                    <button
                      onClick={saveConfiguration}
                      disabled={loading || !connection.name || !connection.url || !connection.email || !connection.token}
                      className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {loading && selectedConfigId ? 'Updating...' : loading ? 'Saving...' : selectedConfigId ? 'Update Configuration' : 'Save Configuration'}
                    </button>
                    
                    <button
                      onClick={clearForm}
                      className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md shadow-sm text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                    >
                      Clear Form
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Project Discovery Tab */}
          {activeTab === 'discovery' && (
            <div className="space-y-6">
              <div className="card">
                <div className="card-header">
                  <h3 className="text-lg font-medium text-gray-900">JIRA Sprint Discovery</h3>
                  <p className="text-sm text-gray-500">Search and select active and future sprints for import</p>
                </div>
                <div className="card-body space-y-6">
                  {/* Sprint Search and Filter */}
                  <div className="flex flex-col sm:flex-row gap-4">
                    <div className="flex-1">
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Search Sprints
                      </label>
                      <div className="flex">
                        <input
                          type="text"
                          value={projectSearch}
                          onChange={(e) => setProjectSearch(e.target.value)}
                          placeholder="Search by sprint name, board, or project..."
                          className="flex-1 px-3 py-2 border border-gray-300 rounded-l-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                        />
                        <button
                          onClick={loadSprints}
                          disabled={discoveryLoading}
                          className="px-4 py-2 bg-indigo-600 text-white rounded-r-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
                        >
                          {discoveryLoading ? 'Searching...' : 'Search'}
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Sprints List */}
                  {projects.length > 0 && (
                    <div>
                      <h4 className="text-md font-medium text-gray-900 mb-3">Available Sprints ({projects.length})</h4>
                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                        {projects.map((sprint) => (
                          <div
                            key={sprint.id}
                            onClick={() => selectProject(sprint)}
                            className={`p-4 border-2 rounded-lg cursor-pointer transition-colors ${
                              selectedProject?.id === sprint.id
                                ? 'border-indigo-500 bg-indigo-50'
                                : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                            }`}
                          >
                            <div className="flex items-start justify-between">
                              <div className="flex-1 min-w-0">
                                <h5 className="text-sm font-medium text-gray-900 truncate">
                                  {sprint.name}
                                </h5>
                                <p className="text-xs text-gray-500 font-mono">
                                  {sprint.board?.name} (ID: {sprint.id})
                                </p>
                                {sprint.goal && (
                                  <p className="text-xs text-gray-600 mt-1 line-clamp-2">
                                    {sprint.goal}
                                  </p>
                                )}
                                <div className="flex items-center mt-2 text-xs text-gray-500">
                                  <span className="mr-2">
                                    {sprint.startDate && new Date(sprint.startDate).toLocaleDateString()}
                                    {sprint.endDate && ` - ${new Date(sprint.endDate).toLocaleDateString()}`}
                                  </span>
                                </div>
                              </div>
                              <div className="ml-3 flex-shrink-0 text-center">
                                <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                                  sprint.state === 'active' ? 'bg-green-100 text-green-800' :
                                  sprint.state === 'future' ? 'bg-blue-100 text-blue-800' :
                                  'bg-gray-100 text-gray-800'
                                }`}>
                                  {sprint.state}
                                </span>
                              </div>
                            </div>
                            <div className="mt-2 flex items-center justify-between">
                              <span className="text-xs text-gray-500 capitalize">
                                {project.projectTypeKey}
                              </span>
                              {project.permissions.browse && (
                                <span className="text-xs text-green-600">✓ Access</span>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Boards List */}
                  {selectedProject && boards.length > 0 && (
                    <div>
                      <div className="flex items-center justify-between mb-3">
                        <h4 className="text-md font-medium text-gray-900">
                          Boards in {selectedProject.name} ({boards.length})
                        </h4>
                        <select
                          value={boardTypeFilter}
                          onChange={(e) => setBoardTypeFilter(e.target.value)}
                          className="text-sm border border-gray-300 rounded-md px-3 py-1 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                        >
                          <option value="">All Types</option>
                          <option value="scrum">Scrum</option>
                          <option value="kanban">Kanban</option>
                        </select>
                      </div>
                      
                      <div className="space-y-3">
                        {boards.map((board) => (
                          <div
                            key={board.id}
                            className={`p-4 border rounded-lg transition-colors ${
                              selectedBoards.includes(board.id)
                                ? 'border-indigo-500 bg-indigo-50'
                                : 'border-gray-200 hover:border-gray-300'
                            }`}
                          >
                            <div className="flex items-start justify-between">
                              <div className="flex items-start space-x-3">
                                <input
                                  type="checkbox"
                                  checked={selectedBoards.includes(board.id)}
                                  onChange={() => toggleBoardSelection(board.id)}
                                  className="mt-1 h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                                />
                                <div className="flex-1 min-w-0">
                                  <h5 className="text-sm font-medium text-gray-900">
                                    {board.name}
                                  </h5>
                                  <div className="flex items-center space-x-2 mt-1">
                                    <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                                      board.configuration.is_scrum 
                                        ? 'bg-green-100 text-green-800' 
                                        : 'bg-blue-100 text-blue-800'
                                    }`}>
                                      {board.type}
                                    </span>
                                    {board.configuration.supports_sprints && (
                                      <span className="text-xs text-gray-500">
                                        {board.sprint_count} sprints
                                      </span>
                                    )}
                                  </div>
                                  {board.active_sprint && (
                                    <p className="text-xs text-gray-600 mt-1">
                                      Active: {board.active_sprint.name}
                                    </p>
                                  )}
                                </div>
                              </div>
                              <div className="flex items-center space-x-2">
                                {board.permissions.view && (
                                  <span className="text-xs text-green-600">✓ View</span>
                                )}
                                {board.configuration.supports_sprints && (
                                  <span className="text-xs text-blue-600">Sprint Support</span>
                                )}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>

                      {selectedBoards.length > 0 && (
                        <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
                          <div className="flex items-center justify-between">
                            <div>
                              <p className="text-sm font-medium text-green-800">
                                {selectedBoards.length} board(s) selected
                              </p>
                              <p className="text-xs text-green-600">
                                Ready to configure for sprint import
                              </p>
                            </div>
                            <button
                              onClick={confirmSelection}
                              disabled={loading}
                              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50"
                            >
                              {loading ? 'Configuring...' : 'Confirm Selection'}
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {discoveryLoading && (
                    <div className="text-center py-8">
                      <div className="inline-flex items-center">
                        <span className="animate-spin inline-block w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full mr-3"></span>
                        Loading JIRA data...
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Selection Result Tab */}
          {activeTab === 'selection' && selectionResult && (
            <div className="space-y-6">
              <div className="card">
                <div className="card-header">
                  <h3 className="text-lg font-medium text-gray-900">Project Selection Confirmed</h3>
                  <p className="text-sm text-gray-500">Your JIRA project and boards have been configured</p>
                </div>
                <div className="card-body space-y-4">
                  <div className="bg-green-50 border border-green-200 rounded-md p-4">
                    <div className="flex">
                      <div className="flex-shrink-0">
                        <span className="text-green-400 text-xl">✅</span>
                      </div>
                      <div className="ml-3">
                        <h4 className="text-sm font-medium text-green-800">
                          Configuration Complete
                        </h4>
                        <div className="mt-2 text-sm text-green-700">
                          <p><strong>Project:</strong> {selectionResult.project.name} ({selectionResult.project.key})</p>
                          <p><strong>Boards:</strong> {selectionResult.boards.length} selected</p>
                          <p><strong>Selected at:</strong> {new Date(selectionResult.selected_at).toLocaleString()}</p>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div>
                    <h4 className="text-md font-medium text-gray-900 mb-3">Selected Boards</h4>
                    <div className="space-y-2">
                      {selectionResult.boards.map((board: any) => (
                        <div key={board.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                          <div>
                            <span className="text-sm font-medium text-gray-900">{board.name}</span>
                            <span className="ml-2 text-xs text-gray-500">({board.type})</span>
                          </div>
                          {board.supports_sprints && (
                            <span className="text-xs text-blue-600">Sprint Support</span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>

                  <div>
                    <h4 className="text-md font-medium text-gray-900 mb-3">Next Steps</h4>
                    <ul className="space-y-2">
                      {selectionResult.next_steps.map((step: string, index: number) => (
                        <li key={index} className="flex items-start text-sm text-gray-600">
                          <span className="text-indigo-500 mr-2">{index + 1}.</span>
                          {step}
                        </li>
                      ))}
                    </ul>
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