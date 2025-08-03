#!/usr/bin/env node

/**
 * Epic 051 Frontend Application Validation Test
 * Comprehensive testing of frontend authentication and API integration
 */

const { execSync } = require('child_process');
const https = require('https');
const http = require('http');

// Test Configuration
const BACKEND_URL = 'http://localhost:8000';
const FRONTEND_URL = 'http://localhost:3002';
const TEST_CREDENTIALS = {
  email: 'admin@sprint-reports.com',
  password: 'admin123'
};

// Colors for console output
const colors = {
  green: '\x1b[32m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  reset: '\x1b[0m',
  bold: '\x1b[1m'
};

function log(message, color = 'reset') {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

function logStep(step, message) {
  log(`\n${step}. ${message}`, 'blue');
}

function logSuccess(message) {
  log(`✅ ${message}`, 'green');
}

function logError(message) {
  log(`❌ ${message}`, 'red');
}

function logWarning(message) {
  log(`⚠️  ${message}`, 'yellow');
}

// HTTP Request Helper
function makeRequest(url, options = {}) {
  return new Promise((resolve, reject) => {
    const protocol = url.startsWith('https') ? https : http;
    const req = protocol.request(url, options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          const result = {
            statusCode: res.statusCode,
            headers: res.headers,
            body: data,
            json: null
          };
          
          if (res.headers['content-type']?.includes('application/json')) {
            result.json = JSON.parse(data);
          }
          
          resolve(result);
        } catch (error) {
          reject(error);
        }
      });
    });
    
    req.on('error', reject);
    
    if (options.body) {
      req.write(options.body);
    }
    
    req.end();
  });
}

// Test Suite
class Epic051ValidationSuite {
  constructor() {
    this.results = {
      total: 0,
      passed: 0,
      failed: 0,
      tests: []
    };
  }

  async runTest(name, testFn) {
    this.results.total++;
    try {
      await testFn();
      this.results.passed++;
      logSuccess(`${name} - PASSED`);
      this.results.tests.push({ name, status: 'PASSED' });
    } catch (error) {
      this.results.failed++;
      logError(`${name} - FAILED: ${error.message}`);
      this.results.tests.push({ name, status: 'FAILED', error: error.message });
    }
  }

  async validateBackendHealth() {
    const response = await makeRequest(`${BACKEND_URL}/health`);
    if (response.statusCode !== 200) {
      throw new Error(`Backend health check failed: ${response.statusCode}`);
    }
    if (!response.json || response.json.status !== 'healthy') {
      throw new Error('Backend not healthy');
    }
  }

  async validateFrontendServing() {
    const response = await makeRequest(FRONTEND_URL);
    if (response.statusCode !== 200 && response.statusCode !== 302) {
      throw new Error(`Frontend not responding: ${response.statusCode}`);
    }
  }

  async validateBackendAuthentication() {
    const response = await makeRequest(`${BACKEND_URL}/api/v1/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(TEST_CREDENTIALS)
    });

    if (response.statusCode !== 200) {
      throw new Error(`Authentication failed: ${response.statusCode}`);
    }

    if (!response.json || !response.json.token || !response.json.user) {
      throw new Error('Invalid authentication response format');
    }

    // Store token for subsequent tests
    this.authToken = response.json.token.access_token;
    this.user = response.json.user;
  }

  async validateProtectedEndpoint() {
    if (!this.authToken) {
      throw new Error('No auth token available');
    }

    const response = await makeRequest(`${BACKEND_URL}/api/v1/users/me`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${this.authToken}`
      }
    });

    if (response.statusCode !== 200) {
      throw new Error(`Protected endpoint failed: ${response.statusCode}`);
    }

    if (!response.json || response.json.email !== TEST_CREDENTIALS.email) {
      throw new Error('Protected endpoint returned incorrect user data');
    }
  }

  async validateSprintsEndpoint() {
    if (!this.authToken) {
      throw new Error('No auth token available');
    }

    const response = await makeRequest(`${BACKEND_URL}/api/v1/sprints/`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${this.authToken}`
      }
    });

    if (response.statusCode !== 200) {
      throw new Error(`Sprints endpoint failed: ${response.statusCode}`);
    }

    // Sprints endpoint should return an array (even if empty)
    if (!response.json || !Array.isArray(response.json)) {
      throw new Error('Sprints endpoint returned invalid format');
    }
  }

  async validateCORSConfiguration() {
    const response = await makeRequest(`${BACKEND_URL}/api/v1/health`, {
      method: 'OPTIONS',
      headers: {
        'Origin': FRONTEND_URL,
        'Access-Control-Request-Method': 'GET',
        'Access-Control-Request-Headers': 'Authorization,Content-Type'
      }
    });

    if (response.statusCode !== 200) {
      logWarning('CORS preflight request failed - this may affect frontend integration');
    }
  }

  async validateEnvironmentConfiguration() {
    // Check if required environment variables are configured
    const configEndpoint = `${BACKEND_URL}/api/v1/health`;
    const response = await makeRequest(configEndpoint);
    
    if (response.statusCode !== 200) {
      throw new Error('Backend configuration check failed');
    }

    // Validate service name and version
    if (!response.json.service || !response.json.version) {
      throw new Error('Backend missing service identification');
    }
  }

  async run() {
    log('🚀 Epic 051 Frontend Application Validation Suite', 'bold');
    log('=' * 60);

    logStep(1, 'Validating Backend Health');
    await this.runTest('Backend Health Check', () => this.validateBackendHealth());

    logStep(2, 'Validating Frontend Serving');
    await this.runTest('Frontend Serving Check', () => this.validateFrontendServing());

    logStep(3, 'Validating Backend Authentication');
    await this.runTest('Backend Authentication', () => this.validateBackendAuthentication());

    logStep(4, 'Validating Protected Endpoint Access');
    await this.runTest('Protected Endpoint Access', () => this.validateProtectedEndpoint());

    logStep(5, 'Validating Sprints API Endpoint');
    await this.runTest('Sprints API Endpoint', () => this.validateSprintsEndpoint());

    logStep(6, 'Validating CORS Configuration');
    await this.runTest('CORS Configuration', () => this.validateCORSConfiguration());

    logStep(7, 'Validating Environment Configuration');
    await this.runTest('Environment Configuration', () => this.validateEnvironmentConfiguration());

    // Summary
    log('\n' + '=' * 60, 'bold');
    log('🔍 VALIDATION SUMMARY', 'bold');
    log('=' * 60);
    
    log(`Total Tests: ${this.results.total}`);
    logSuccess(`Passed: ${this.results.passed}`);
    if (this.results.failed > 0) {
      logError(`Failed: ${this.results.failed}`);
    }

    const successRate = ((this.results.passed / this.results.total) * 100).toFixed(1);
    log(`Success Rate: ${successRate}%`);

    if (this.results.failed === 0) {
      log('\n🎉 ALL TESTS PASSED - Epic 051 Ready for Integration!', 'green');
      return true;
    } else {
      log('\n🚨 SOME TESTS FAILED - Review issues before proceeding', 'red');
      return false;
    }
  }
}

// Main execution
async function main() {
  try {
    const suite = new Epic051ValidationSuite();
    const success = await suite.run();
    process.exit(success ? 0 : 1);
  } catch (error) {
    logError(`Test suite failed to run: ${error.message}`);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = Epic051ValidationSuite;