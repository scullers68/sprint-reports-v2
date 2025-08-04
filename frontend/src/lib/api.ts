import { 
  ApiResponse, 
  ApiError, 
  AuthResponse, 
  LoginRequest, 
  RegisterRequest,
  SSOConfig,
  User,
  Sprint,
  SprintAnalysis,
  RequestConfig,
  PaginationParams,
  FilterParams
} from '@/types/api';

// API Configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001';
const API_VERSION = 'v1';
const DEFAULT_TIMEOUT = 30000; // 30 seconds
const MAX_RETRIES = 3;

// Custom Error Classes
export class ApiRequestError extends Error {
  constructor(
    message: string,
    public status: number,
    public code?: string,
    public details?: any
  ) {
    super(message);
    this.name = 'ApiRequestError';
  }
}

export class NetworkError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'NetworkError';
  }
}

// Token Management
class TokenManager {
  private static instance: TokenManager;
  private token: string | null = null;
  private tokenType: string = 'Bearer';
  private expiresAt: number | null = null;

  static getInstance(): TokenManager {
    if (!TokenManager.instance) {
      TokenManager.instance = new TokenManager();
    }
    return TokenManager.instance;
  }

  setToken(token: string, tokenType: string = 'Bearer', expiresIn?: number) {
    this.token = token;
    this.tokenType = tokenType;
    
    if (expiresIn) {
      this.expiresAt = Date.now() + (expiresIn * 1000);
    }
    
    // Store in localStorage for persistence
    if (typeof window !== 'undefined') {
      localStorage.setItem('access_token', token);
      localStorage.setItem('token_type', tokenType);
      if (this.expiresAt) {
        localStorage.setItem('token_expires_at', this.expiresAt.toString());
      }
      
      // Also set cookie for middleware to access
      const expires = expiresIn ? new Date(Date.now() + (expiresIn * 1000)).toUTCString() : '';
      const expiresAttribute = expires ? `; expires=${expires}` : '';
      document.cookie = `access_token=${token}; path=/${expiresAttribute}; SameSite=Lax`;
    }
  }

  getToken(): string | null {
    if (!this.token && typeof window !== 'undefined') {
      this.token = localStorage.getItem('access_token');
      this.tokenType = localStorage.getItem('token_type') || 'Bearer';
      const expiresAt = localStorage.getItem('token_expires_at');
      this.expiresAt = expiresAt ? parseInt(expiresAt) : null;
    }
    return this.token;
  }

  getAuthHeader(): string | null {
    const token = this.getToken();
    const authHeader = token ? `${this.tokenType} ${token}` : null;
    console.log('Getting auth header - token exists:', !!token, 'tokenType:', this.tokenType);
    if (token) {
      // Check if token is expired
      console.log('Token expired:', this.isTokenExpired());
      console.log('Token expires at:', this.expiresAt ? new Date(this.expiresAt).toISOString() : 'not set');
      console.log('Current time:', new Date().toISOString());
    }
    return authHeader;
  }

  isTokenExpired(): boolean {
    if (!this.expiresAt) return false;
    return Date.now() >= this.expiresAt;
  }

  clearToken() {
    this.token = null;
    this.tokenType = 'Bearer';
    this.expiresAt = null;
    
    if (typeof window !== 'undefined') {
      localStorage.removeItem('access_token');
      localStorage.removeItem('token_type');
      localStorage.removeItem('token_expires_at');
      localStorage.removeItem('user');
      
      // Also clear the cookie
      document.cookie = 'access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 UTC; SameSite=Lax';
    }
  }
}

// API Client Class
class ApiClient {
  private baseURL: string;
  private tokenManager: TokenManager;

  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = `${baseURL}/api/${API_VERSION}`;
    this.tokenManager = TokenManager.getInstance();
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit & RequestConfig = {}
  ): Promise<T> {
    const {
      headers = {},
      timeout = DEFAULT_TIMEOUT,
      retries = MAX_RETRIES,
      ...fetchOptions
    } = options;

    // Build URL
    const url = `${this.baseURL}${endpoint}`;

    // Build headers
    const defaultHeaders: Record<string, string> = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };

    // Add auth header if available
    const authHeader = this.tokenManager.getAuthHeader();
    if (authHeader) {
      defaultHeaders.Authorization = authHeader;
    } else {
      console.warn('No auth header available for request to:', endpoint);
    }

    const finalHeaders = { ...defaultHeaders, ...headers };

    // Build request config
    const requestConfig: RequestInit = {
      ...fetchOptions,
      headers: finalHeaders,
    };

    // Add timeout using AbortController
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);
    requestConfig.signal = controller.signal;

    let lastError: Error | null = null;

    // Retry logic
    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        const response = await fetch(url, requestConfig);
        clearTimeout(timeoutId);

        // Handle HTTP errors
        if (!response.ok) {
          const errorData: ApiError | any = await response.json().catch(() => ({
            error: {
              code: 'UNKNOWN_ERROR',
              message: `HTTP ${response.status}: ${response.statusText}`,
            }
          }));

          throw new ApiRequestError(
            errorData.error?.message || `Request failed with status ${response.status}`,
            response.status,
            errorData.error?.code,
            errorData.error?.details
          );
        }

        // Parse response
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
          return await response.json();
        } else {
          return response.text() as unknown as T;
        }

      } catch (error) {
        clearTimeout(timeoutId);
        lastError = error as Error;

        // Don't retry on authentication errors or client errors (4xx)
        if (error instanceof ApiRequestError && error.status >= 400 && error.status < 500) {
          throw error;
        }

        // Don't retry on the last attempt
        if (attempt === retries) {
          break;
        }

        // Wait before retrying (exponential backoff)
        await new Promise(resolve => setTimeout(resolve, Math.pow(2, attempt) * 1000));
      }
    }

    // Throw the last error if all retries failed
    if (lastError) {
      if (lastError.name === 'AbortError') {
        throw new NetworkError('Request timeout');
      }
      throw lastError;
    }

    throw new NetworkError('Request failed after all retries');
  }

  // HTTP Methods
  async get<T>(endpoint: string, params?: Record<string, any>, config?: RequestConfig): Promise<T> {
    const url = params ? `${endpoint}?${new URLSearchParams(params)}` : endpoint;
    return this.request<T>(url, { method: 'GET', ...config });
  }

  async post<T>(endpoint: string, data?: any, config?: RequestConfig): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
      ...config
    });
  }

  async put<T>(endpoint: string, data?: any, config?: RequestConfig): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
      ...config
    });
  }

  async patch<T>(endpoint: string, data?: any, config?: RequestConfig): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PATCH',
      body: data ? JSON.stringify(data) : undefined,
      ...config
    });
  }

  async delete<T>(endpoint: string, config?: RequestConfig): Promise<T> {
    return this.request<T>(endpoint, { method: 'DELETE', ...config });
  }

  // Authentication Methods
  async login(credentials: LoginRequest): Promise<AuthResponse> {
    const response = await this.post<any>('/auth/login', credentials);
    
    // Handle backend response format: { user: {}, token: { access_token, ... } }
    const authResponse: AuthResponse = {
      access_token: response.token.access_token,
      token_type: response.token.token_type,
      expires_in: response.token.expires_in,
      user: response.user
    };
    
    // Store token (ensure Bearer is capitalized per HTTP standard)
    this.tokenManager.setToken(
      authResponse.access_token,
      authResponse.token_type.charAt(0).toUpperCase() + authResponse.token_type.slice(1),
      authResponse.expires_in
    );
    
    // Store user info
    if (typeof window !== 'undefined') {
      localStorage.setItem('user', JSON.stringify(authResponse.user));
    }
    
    return authResponse;
  }

  async register(userData: RegisterRequest): Promise<AuthResponse> {
    const response = await this.post<any>('/auth/register', userData);
    
    // Handle backend response format: { user: {}, token: { access_token, ... } }
    const authResponse: AuthResponse = {
      access_token: response.token.access_token,
      token_type: response.token.token_type,
      expires_in: response.token.expires_in,
      user: response.user
    };
    
    // Store token
    this.tokenManager.setToken(
      authResponse.access_token,
      authResponse.token_type,
      authResponse.expires_in
    );
    
    // Store user info
    if (typeof window !== 'undefined') {
      localStorage.setItem('user', JSON.stringify(authResponse.user));
    }
    
    return authResponse;
  }

  async logout(): Promise<void> {
    try {
      await this.post('/auth/logout');
    } catch (error) {
      // Continue with logout even if API call fails
      console.warn('Logout API call failed:', error);
    } finally {
      this.tokenManager.clearToken();
    }
  }

  async getCurrentUser(): Promise<User> {
    return this.get<User>('/users/me');
  }

  // SSO Methods
  async getSSOConfig(): Promise<SSOConfig> {
    return this.get<SSOConfig>('/auth/sso/config');
  }

  // Sprint Methods
  async getSprintsToProcess(params?: PaginationParams & FilterParams): Promise<ApiResponse<Sprint[]>> {
    return this.get<ApiResponse<Sprint[]>>('/sprints/', params);
  }

  async getSprints(params?: {
    skip?: number;
    limit?: number;
    state?: string;
    active_only?: boolean;
    search?: string;
  }): Promise<Sprint[]> {
    return this.get<Sprint[]>('/sprints/', params);
  }

  async getSprintStats(): Promise<{
    active_sprints: number;
    total_issues: number;
    team_members: number;
  }> {
    // This will call existing endpoints to get aggregate stats
    const [sprints] = await Promise.all([
      this.getSprints({ active_only: true })
    ]);
    
    return {
      active_sprints: sprints.length,
      total_issues: sprints.reduce((sum, sprint) => sum + (sprint.id || 0), 0), // Placeholder logic
      team_members: 15 // Placeholder - could be from another endpoint
    };
  }

  async getSprint(id: number): Promise<Sprint> {
    return this.get<Sprint>(`/sprints/${id}`);
  }

  async getSprintAnalysis(sprintId: number): Promise<SprintAnalysis> {
    return this.get<SprintAnalysis>(`/sprints/${sprintId}/analysis`);
  }

  // JIRA Discovery Methods
  async getJiraProjects(params?: {
    search?: string;
    limit?: number;
  }): Promise<any[]> {
    return this.get<any[]>('/jira/projects', params);
  }

  async searchJiraSprints(params?: {
    search?: string;
    state?: string;
    limit?: number;
  }): Promise<any[]> {
    return this.get<any[]>('/jira/sprints/search', params);
  }

  async getJiraProjectBoards(
    projectKey: string, 
    params?: { board_type?: string }
  ): Promise<any[]> {
    return this.get<any[]>(`/jira/projects/${projectKey}/boards`, params);
  }

  async getJiraBoardConfiguration(boardId: number): Promise<any> {
    return this.get<any>(`/jira/boards/${boardId}/configuration`);
  }

  async selectJiraProject(
    projectKey: string, 
    boardIds: number[]
  ): Promise<any> {
    return this.post<any>(`/jira/projects/${projectKey}/select`, { board_ids: boardIds });
  }

  async testJiraConnection(config: {
    url: string;
    email: string;
    api_token: string;
    auth_method: string;
  }): Promise<any> {
    return this.post<any>('/jira/connection/test', {
      config,
      test_operations: ['server_info', 'projects', 'boards']
    });
  }

  // JIRA Configuration Management Methods
  async createJiraConfiguration(data: {
    name: string;
    description?: string;
    config: {
      url: string;
      email: string;
      api_token: string;
      auth_method: string;
    };
    environment?: string;
    test_connection?: boolean;
  }): Promise<any> {
    return this.post<any>('/jira/configurations', data);
  }

  async getJiraConfigurations(params?: {
    environment?: string;
    status_filter?: string;
    is_active?: boolean;
    limit?: number;
    offset?: number;
  }): Promise<any> {
    return this.get<any>('/jira/configurations', params);
  }

  async getJiraConfiguration(configId: number, includeSensitive: boolean = false): Promise<any> {
    return this.get<any>(`/jira/configurations/${configId}`, { include_sensitive: includeSensitive });
  }

  async updateJiraConfiguration(configId: number, data: {
    name?: string;
    description?: string;
    config?: {
      url?: string;
      email?: string;
      api_token?: string;
      auth_method?: string;
    };
    test_connection?: boolean;
  }): Promise<any> {
    return this.put<any>(`/jira/configurations/${configId}`, data);
  }

  async deleteJiraConfiguration(configId: number): Promise<void> {
    return this.delete<void>(`/jira/configurations/${configId}`);
  }

  async testJiraConfigurationById(configId: number, updateStatus: boolean = true): Promise<any> {
    return this.post<any>(`/jira/configurations/${configId}/test`, { update_status: updateStatus });
  }

  async getDefaultJiraConfiguration(environment: string = 'production'): Promise<any> {
    return this.get<any>('/jira/configurations/default', { environment });
  }

  // Health Check
  async healthCheck(): Promise<{ status: string; timestamp: string }> {
    return this.get<{ status: string; timestamp: string }>('/health');
  }

  // Token Management
  isAuthenticated(): boolean {
    const token = this.tokenManager.getToken();
    return !!token && !this.tokenManager.isTokenExpired();
  }

  clearAuth(): void {
    this.tokenManager.clearToken();
  }
}

// Export singleton instance
export const apiClient = new ApiClient();

// Export utilities
export { TokenManager };
export default apiClient;