'use client';

import { Suspense } from 'react';
import { SSOCallback } from '@/components/auth/SSOCallback';

function SSOCallbackContent() {
  return (
    <SSOCallback
      provider="oauth"
      onAuthSuccess={(response) => {
        console.log('Authentication successful:', response);
      }}
      onAuthError={(error) => {
        console.error('Authentication failed:', error);
      }}
    />
  );
}

export default function SSOCallbackPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    }>
      <SSOCallbackContent />
    </Suspense>
  );
}