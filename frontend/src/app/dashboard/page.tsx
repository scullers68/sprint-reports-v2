'use client';

import { Header } from '@/components/layout/Header';
import { useEffect, useState } from 'react';
import { apiClient } from '@/lib/api';
import Link from 'next/link';

interface DashboardStats {
  active_sprints: number;
  total_issues: number;
  team_members: number;
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        setLoading(true);
        const dashboardStats = await apiClient.getSprintStats();
        setStats(dashboardStats);
        setError(null);
      } catch (err) {
        console.error('Failed to fetch dashboard stats:', err);
        setError('Failed to load dashboard data');
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header />
        <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
          <div className="px-4 py-6 sm:px-0">
            <div className="animate-pulse">
              <div className="page-header">
                <div className="h-8 bg-gray-300 rounded w-1/4 mb-2"></div>
                <div className="h-4 bg-gray-300 rounded w-1/2"></div>
              </div>
              <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 mt-8">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="card">
                    <div className="card-body">
                      <div className="h-16 bg-gray-300 rounded"></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </main>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header />
        <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
          <div className="px-4 py-6 sm:px-0">
            <div className="page-header">
              <h1 className="page-title">Dashboard</h1>
              <p className="page-description">Overview of your sprint management activities</p>
            </div>
            <div className="mt-8 card">
              <div className="card-body">
                <div className="text-red-600">
                  <p className="font-medium">Error loading dashboard</p>
                  <p className="text-sm">{error}</p>
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>
    );
  }

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
                      {stats?.active_sprints || 0}
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
                      {stats?.total_issues || 0}
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
                      {stats?.team_members || 0}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-8">
            <div className="card">
              <div className="card-header flex justify-between items-center">
                <h3 className="text-lg font-medium text-gray-900">Quick Actions</h3>
              </div>
              <div className="card-body">
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  <Link 
                    href="/sprints" 
                    className="group relative rounded-lg border border-gray-300 bg-white px-6 py-5 shadow-sm hover:shadow-md focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 transition-all duration-200"
                  >
                    <div>
                      <span className="rounded-lg inline-flex p-3 bg-indigo-50 text-indigo-600 ring-4 ring-white">
                        <span className="text-xl">📋</span>
                      </span>
                    </div>
                    <div className="mt-4">
                      <h3 className="text-lg font-medium text-gray-900 group-hover:text-indigo-600">
                        View All Sprints
                      </h3>
                      <p className="text-sm text-gray-500">
                        Browse and manage all sprint data
                      </p>
                    </div>
                  </Link>
                  
                  <div className="group relative rounded-lg border border-gray-300 bg-gray-50 px-6 py-5 shadow-sm">
                    <div>
                      <span className="rounded-lg inline-flex p-3 bg-gray-100 text-gray-400 ring-4 ring-white">
                        <span className="text-xl">📊</span>
                      </span>
                    </div>
                    <div className="mt-4">
                      <h3 className="text-lg font-medium text-gray-400">
                        Analytics
                      </h3>
                      <p className="text-sm text-gray-400">
                        Coming soon
                      </p>
                    </div>
                  </div>
                  
                  <div className="group relative rounded-lg border border-gray-300 bg-gray-50 px-6 py-5 shadow-sm">
                    <div>
                      <span className="rounded-lg inline-flex p-3 bg-gray-100 text-gray-400 ring-4 ring-white">
                        <span className="text-xl">⚙️</span>
                      </span>
                    </div>
                    <div className="mt-4">
                      <h3 className="text-lg font-medium text-gray-400">
                        Settings
                      </h3>
                      <p className="text-sm text-gray-400">
                        Coming soon
                      </p>
                    </div>
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