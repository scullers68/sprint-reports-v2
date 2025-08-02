import { Header } from '@/components/layout/Header';

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          <div className="page-header">
            <h1 className="page-title">Dashboard</h1>
            <p className="page-description">
              Overview of your sprint management activities and key metrics
            </p>
          </div>

          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            <div className="card">
              <div className="card-body">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className="text-3xl">🎯</div>
                  </div>
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-500 truncate">
                      Active Sprints
                    </p>
                    <p className="text-2xl font-semibold text-gray-900">
                      3
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <div className="card">
              <div className="card-body">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className="text-3xl">📋</div>
                  </div>
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-500 truncate">
                      Total Issues
                    </p>
                    <p className="text-2xl font-semibold text-gray-900">
                      127
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <div className="card">
              <div className="card-body">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className="text-3xl">👥</div>
                  </div>
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-500 truncate">
                      Team Members
                    </p>
                    <p className="text-2xl font-semibold text-gray-900">
                      15
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-8">
            <div className="card">
              <div className="card-header">
                <h3 className="text-lg font-medium text-gray-900">Recent Activity</h3>
              </div>
              <div className="card-body">
                <p className="text-gray-500">
                  Sprint management features will be available once the backend integration is complete.
                </p>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}