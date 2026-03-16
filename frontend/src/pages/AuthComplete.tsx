import React, { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';
import LoadingSpinner from '../components/ui/LoadingSpinner';

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
      } catch (err: unknown) {
        console.error('Auth completion failed:', err);
        const axiosErr = err as { response?: { data?: { detail?: string }; status?: number } };
        const detail = axiosErr?.response?.data?.detail;
        setError(detail && typeof detail === 'string' ? detail : 'Authentication failed. Please try again.');
        setTimeout(() => navigate('/login'), 3000);
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
      <LoadingSpinner label="Completing authentication..." />
    </div>
  );
};

export default AuthComplete;
