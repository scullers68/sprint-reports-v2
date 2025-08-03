'use client';

import { Header } from '@/components/layout/Header';
import { useEffect, useState } from 'react';
import { apiClient } from '@/lib/api';
import { Sprint } from '@/types/api';
import Link from 'next/link';

export default function SprintsPage() {
  const [sprints, setSprints] = useState<Sprint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [stateFilter, setStateFilter] = useState<string>('');
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;

  // Derived state for filtering and pagination
  const filteredSprints = sprints.filter(sprint => {
    const matchesSearch = sprint.name.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesState = !stateFilter || sprint.state === stateFilter;
    return matchesSearch && matchesState;
  });

  const totalPages = Math.ceil(filteredSprints.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const paginatedSprints = filteredSprints.slice(startIndex, startIndex + itemsPerPage);

  useEffect(() => {
    const fetchSprints = async () => {
      try {
        setLoading(true);
        const sprintsData = await apiClient.getSprints();
        setSprints(sprintsData);
        setError(null);
      } catch (err) {
        console.error('Failed to fetch sprints:', err);
        setError('Failed to load sprints');
      } finally {
        setLoading(false);
      }
    };

    fetchSprints();
  }, []);

  // Reset to first page when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm, stateFilter]);

  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(e.target.value);
  };

  const handleStateFilter = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setStateFilter(e.target.value);
  };

  const getStateColor = (state: string) => {
    switch (state) {
      case 'active':
        return 'bg-green-100 text-green-800';
      case 'future':
        return 'bg-blue-100 text-blue-800';
      case 'closed':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'Not set';
    return new Date(dateString).toLocaleDateString();
  };

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
              <div className="mt-8 space-y-4">
                {[1, 2, 3, 4, 5].map((i) => (
                  <div key={i} className="card">
                    <div className="card-body">
                      <div className="h-6 bg-gray-300 rounded w-3/4 mb-2"></div>
                      <div className="h-4 bg-gray-300 rounded w-1/2"></div>
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
              <h1 className="page-title">Sprints</h1>
              <p className="page-description">Manage and view all sprint data</p>
            </div>
            <div className="mt-8 card">
              <div className="card-body">
                <div className="text-red-600">
                  <p className="font-medium">Error loading sprints</p>
                  <p className="text-sm">{error}</p>
                  <button 
                    onClick={() => window.location.reload()} 
                    className="mt-2 inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
                  >
                    Retry
                  </button>
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
            <h1 className="page-title">Sprints</h1>
            <p className="page-description">
              Manage and view all sprint data from your JIRA integration
            </p>
          </div>

          {/* Search and Filter Section */}
          <div className="mt-8 card">
            <div className="card-body">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="md:col-span-2">
                  <label htmlFor="search" className="block text-sm font-medium text-gray-700 mb-1">
                    Search Sprints
                  </label>
                  <input
                    type="text"
                    id="search"
                    placeholder="Search by sprint name..."
                    value={searchTerm}
                    onChange={handleSearch}
                    className="shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md px-3 py-2"
                  />
                </div>
                <div>
                  <label htmlFor="state-filter" className="block text-sm font-medium text-gray-700 mb-1">
                    Filter by State
                  </label>
                  <select
                    id="state-filter"
                    value={stateFilter}
                    onChange={handleStateFilter}
                    className="shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md px-3 py-2"
                  >
                    <option value="">All States</option>
                    <option value="active">Active</option>
                    <option value="future">Future</option>
                    <option value="closed">Closed</option>
                  </select>
                </div>
              </div>
              
              <div className="mt-4 flex justify-between items-center text-sm text-gray-600">
                <span>
                  Showing {paginatedSprints.length} of {filteredSprints.length} sprints
                  {searchTerm && ` matching "${searchTerm}"`}
                  {stateFilter && ` with state "${stateFilter}"`}
                </span>
              </div>
            </div>
          </div>

          {/* Sprint List */}
          <div className="mt-8 space-y-4">
            {paginatedSprints.length === 0 ? (
              <div className="card">
                <div className="card-body text-center py-12">
                  <div className="text-6xl mb-4">📋</div>
                  <h3 className="text-lg font-medium text-gray-900 mb-2">No sprints found</h3>
                  <p className="text-gray-500">
                    {searchTerm || stateFilter 
                      ? 'Try adjusting your search or filter criteria.'
                      : 'No sprints are available at the moment.'
                    }
                  </p>
                </div>
              </div>
            ) : (
              paginatedSprints.map((sprint) => (
                <div key={sprint.id} className="card hover:shadow-md transition-shadow">
                  <div className="card-body">
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="flex items-center space-x-3">
                          <h3 className="text-lg font-medium text-gray-900">
                            {sprint.name}
                          </h3>
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStateColor(sprint.state)}`}>
                            {sprint.state.charAt(0).toUpperCase() + sprint.state.slice(1)}
                          </span>
                        </div>
                        
                        {sprint.goal && (
                          <p className="mt-2 text-sm text-gray-600">
                            <span className="font-medium">Goal:</span> {sprint.goal}
                          </p>
                        )}
                        
                        <div className="mt-2 grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm text-gray-500">
                          <div>
                            <span className="font-medium">Start Date:</span> {formatDate(sprint.start_date)}
                          </div>
                          <div>
                            <span className="font-medium">End Date:</span> {formatDate(sprint.end_date)}
                          </div>
                          <div>
                            <span className="font-medium">JIRA ID:</span> {sprint.jira_sprint_id}
                          </div>
                        </div>
                      </div>
                      
                      <div className="flex items-center space-x-2">
                        <Link
                          href={`/sprints/${sprint.id}`}
                          className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                        >
                          View Details
                        </Link>
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="mt-8 flex items-center justify-between">
              <div className="flex-1 flex justify-between sm:hidden">
                <button
                  onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                  disabled={currentPage === 1}
                  className="relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Previous
                </button>
                <button
                  onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                  disabled={currentPage === totalPages}
                  className="ml-3 relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next
                </button>
              </div>
              
              <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm text-gray-700">
                    Showing page <span className="font-medium">{currentPage}</span> of{' '}
                    <span className="font-medium">{totalPages}</span>
                  </p>
                </div>
                <div>
                  <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px">
                    <button
                      onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                      disabled={currentPage === 1}
                      className="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Previous
                    </button>
                    
                    {/* Page numbers */}
                    {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                      let pageNum;
                      if (totalPages <= 5) {
                        pageNum = i + 1;
                      } else if (currentPage <= 3) {
                        pageNum = i + 1;
                      } else if (currentPage >= totalPages - 2) {
                        pageNum = totalPages - 4 + i;
                      } else {
                        pageNum = currentPage - 2 + i;
                      }
                      
                      return (
                        <button
                          key={pageNum}
                          onClick={() => setCurrentPage(pageNum)}
                          className={`relative inline-flex items-center px-4 py-2 border text-sm font-medium ${
                            currentPage === pageNum
                              ? 'z-10 bg-indigo-50 border-indigo-500 text-indigo-600'
                              : 'bg-white border-gray-300 text-gray-500 hover:bg-gray-50'
                          }`}
                        >
                          {pageNum}
                        </button>
                      );
                    })}
                    
                    <button
                      onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                      disabled={currentPage === totalPages}
                      className="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Next
                    </button>
                  </nav>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}