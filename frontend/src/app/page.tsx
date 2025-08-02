import Link from 'next/link';
import { Header } from '@/components/layout/Header';

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          <div className="text-center">
            <h1 className="text-4xl font-bold tracking-tight text-gray-900 sm:text-6xl">
              Sprint Reports v2
            </h1>
            <p className="mt-6 text-lg leading-8 text-gray-600 max-w-2xl mx-auto">
              Modern sprint management platform that empowers agile teams with intelligent 
              queue generation, comprehensive analytics, and seamless integrations.
            </p>
            <div className="mt-10 flex items-center justify-center gap-x-6">
              <Link
                href="/login"
                className="btn-primary"
              >
                Get Started
              </Link>
              <Link
                href="/dashboard"
                className="btn-outline"
              >
                View Dashboard
              </Link>
            </div>
          </div>

          <div className="mt-16 grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-3">
            <div className="card">
              <div className="card-body">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className="text-3xl">⚡</div>
                  </div>
                  <div className="ml-4">
                    <h3 className="text-lg font-medium text-gray-900">Smart Queue Generation</h3>
                    <p className="mt-1 text-sm text-gray-500">
                      AI-powered workload distribution across discipline teams
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <div className="card">
              <div className="card-body">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className="text-3xl">📊</div>
                  </div>
                  <div className="ml-4">
                    <h3 className="text-lg font-medium text-gray-900">Real-time Analytics</h3>
                    <p className="mt-1 text-sm text-gray-500">
                      Comprehensive sprint insights and performance tracking
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <div className="card">
              <div className="card-body">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className="text-3xl">🔗</div>
                  </div>
                  <div className="ml-4">
                    <h3 className="text-lg font-medium text-gray-900">JIRA Integration</h3>
                    <p className="mt-1 text-sm text-gray-500">
                      Seamless bi-directional sync with advanced field mapping
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}