import { FullAnalysisResponse } from './types';

export async function fetchFullAnalysis(): Promise<FullAnalysisResponse> {
  const response = await fetch('/api/demo/full-analysis');
  if (!response.ok) {
    throw new Error(`Failed to fetch analysis data: ${response.statusText}`);
  }
  return response.json();
}

export async function refreshAnalysis(): Promise<FullAnalysisResponse> {
  const refreshRes = await fetch('/api/demo/refresh', { method: 'POST' });
  if (!refreshRes.ok) {
    throw new Error(`Failed to refresh analysis: ${refreshRes.statusText}`);
  }
  return fetchFullAnalysis();
}
