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
    return token ? `${this.tokenType} ${token}` : null;
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
    const response = await this.post<AuthResponse>('/auth/login', credentials);
    
    // Store token
    this.tokenManager.setToken(
      response.access_token,
      response.token_type,
      response.expires_in
    );
    
    // Store user info
    if (typeof window !== 'undefined') {
      localStorage.setItem('user', JSON.stringify(response.user));
    }
    
    return response;
  }

  async register(userData: RegisterRequest): Promise<AuthResponse> {
    const response = await this.post<AuthResponse>('/auth/register', userData);
    
    // Store token
    this.tokenManager.setToken(
      response.access_token,
      response.token_type,
      response.expires_in
    );
    
    // Store user info
    if (typeof window !== 'undefined') {
      localStorage.setItem('user', JSON.stringify(response.user));
    }
    
    return response;
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
    return this.get<User>('/auth/me');
  }

  // SSO Methods
  async getSSOConfig(): Promise<SSOConfig> {
    return this.get<SSOConfig>('/auth/sso/config');
  }

  // Sprint Methods
  async getSprintsToProcess(params?: PaginationParams & FilterParams): Promise<ApiResponse<Sprint[]>> {
    return this.get<ApiResponse<Sprint[]>>('/sprints/', params);
  }

  async getSprint(id: number): Promise<Sprint> {
    return this.get<Sprint>(`/sprints/${id}`);
  }

  async getSprintAnalysis(sprintId: number): Promise<SprintAnalysis> {
    return this.get<SprintAnalysis>(`/sprints/${sprintId}/analysis`);
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