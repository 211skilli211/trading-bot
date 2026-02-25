import useSWR from 'swr';
import { api } from '../api/client';
import { Price } from '../types';

export function usePrices() {
  const { data, error, isLoading } = useSWR<Price[]>(
    'prices',
    () => api.getPrices(),
    { refreshInterval: 30000 }
  );
  
  return {
    prices: data || [],
    isLoading,
    error,
  };
}
