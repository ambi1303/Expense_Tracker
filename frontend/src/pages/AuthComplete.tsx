import React, { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';

const AuthComplete: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { checkAuth } = useAuth();
  const [error, setError] = React.useState<string | null>(null);

  useEffect(() => {
    const completeAuth = async () => {
      const token = searchParams.get('token');
      
      if (!token) {
        setError('No authentication token received');
        setTimeout(() => navigate('/login'), 2000);
        return;
      }

      try {
        // Set the session cookie via backend
        await api.post('/auth/set-session', null, {
          params: { token }
        });

        // Refresh auth state
        await checkAuth();

        // Redirect to dashboard
        navigate('/dashboard');
      } catch (err) {
        console.error('Auth completion failed:', err);
        setError('Authentication failed. Please try again.');
        setTimeout(() => navigate('/login'), 2000);
      }
    };

    completeAuth();
  }, [searchParams, navigate, checkAuth]);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="text-center">
          <div className="text-red-600 dark:text-red-400 text-xl mb-4">❌</div>
          <p className="text-gray-900 dark:text-white">{error}</p>
          <p className="text-gray-600 dark:text-gray-400 text-sm mt-2">
            Redirecting to login...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
      <div className="text-center">
        <svg
          className="animate-spin h-12 w-12 text-primary-600 mx-auto mb-4"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          ></circle>
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          ></path>
        </svg>
        <p className="text-gray-900 dark:text-white">Completing authentication...</p>
      </div>
    </div>
  );
};

export default AuthComplete;
