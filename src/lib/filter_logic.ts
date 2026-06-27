export type Provider = {
  id: string;
  name: string;
  deployment_type: 'api' | 'self_hosted' | 'both';
  model_category?: string;
  context_tokens?: number | null;
  api_input_per_million?: number | null;
};

export function filterProviders(
  providers: Provider[],
  deploymentFilter: string,
  categoryFilter: string,
): Provider[] {
  return providers.filter((p) => {
    const deployOk =
      !deploymentFilter ||
      p.deployment_type === deploymentFilter ||
      (deploymentFilter === 'api' && p.deployment_type === 'both') ||
      (deploymentFilter === 'self_hosted' && p.deployment_type === 'both');
    const catOk = !categoryFilter || p.model_category === categoryFilter;
    return deployOk && catOk;
  });
}

export function sortProviders(
  providers: Provider[],
  sortKey: 'context' | 'price',
  direction: 'asc' | 'desc' = 'desc',
): Provider[] {
  const sorted = [...providers].sort((a, b) => {
    const av =
      sortKey === 'context'
        ? a.context_tokens ?? -1
        : a.api_input_per_million ?? -1;
    const bv =
      sortKey === 'context'
        ? b.context_tokens ?? -1
        : b.api_input_per_million ?? -1;
    return av - bv;
  });
  return direction === 'desc' ? sorted.reverse() : sorted;
}
