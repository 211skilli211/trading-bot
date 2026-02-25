import useSWR from 'swr';
import { api } from '../api/client';
import { Portfolio } from '../types';

export function usePortfolio() {
  const { data, error, isLoading, mutate } = useSWR<Portfolio>(
    'portfolio',
    () => api.getPortfolio(),
    { refreshInterval: 60000 }
  );
  
  return {
    portfolio: data,
    isLoading,
    error,
    refresh: mutate,
  };
}
