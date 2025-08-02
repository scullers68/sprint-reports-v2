// API Response Types
export interface ApiResponse<T = any> {
  data?: T;
  meta?: {
    total?: number;
    page?: number;
    per_page?: number;
  };
  links?: {
    self?: string;
    next?: string;
    prev?: string;
  };
}

export interface ApiError {
  error: {
    code: string;
    message: string;
    details?: Array<{
      field: string;
      message: string;
    }>;
    request_id?: string;
  };
}

// Authentication Types
export interface User {
  id: number;
  email: string;
  username: string;
  full_name: string;
  is_active: boolean;
  role: string;
  sso_provider?: string;
  jira_account_id?: string;
  created_at: string;
  updated_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  username: string;
  full_name: string;
  password: string;
}

// SSO Types
export interface SSOProvider {
  type: string;
  name: string;
  initiate_url: string;
  callback_url: string;
  client_id?: string;
  tenant_id?: string;
  entity_id?: string;
}

export interface SSOConfig {
  sso_enabled: boolean;
  auto_provision_users: boolean;
  allowed_domains: string[];
  providers: SSOProvider[];
}

// Sprint Types
export interface Sprint {
  id: number;
  jira_sprint_id: number;
  name: string;
  state: 'future' | 'active' | 'closed';
  start_date?: string;
  end_date?: string;
  goal?: string;
  created_at: string;
  updated_at: string;
}

export interface SprintAnalysis {
  id: number;
  sprint_id: number;
  analysis_type: string;
  total_issues: number;
  total_story_points: number;
  discipline_breakdown: Record<string, any>;
  created_at: string;
}

// API Client Types
export interface RequestConfig {
  headers?: Record<string, string>;
  timeout?: number;
  retries?: number;
}

export interface PaginationParams {
  page?: number;
  per_page?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface FilterParams {
  [key: string]: string | number | boolean | undefined;
}