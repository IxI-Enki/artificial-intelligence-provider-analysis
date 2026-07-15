export interface CatalogModel {
  id: string;
  vendor: string;
  name: string;
  display_name?: string;
  context_tokens?: number | null;
  max_output_tokens?: number | null;
  api_input_per_million?: number | null;
  api_output_per_million?: number | null;
  modality?: string | null;
  weight_access: 'open' | 'closed' | 'unknown';
  hugging_face_id?: string | null;
  supports_tools?: boolean;
  supports_structured_outputs?: boolean;
  is_free?: boolean;
  description?: string | null;
}

export type CatalogSortKey =
  | 'vendor'
  | 'name'
  | 'context'
  | 'input_price'
  | 'output_price';

export function filterCatalogModels(
  models: CatalogModel[],
  vendor: string,
  weightAccess: string,
  freeOnly: boolean,
  query: string,
): CatalogModel[] {
  const q = query.trim().toLowerCase();
  return models.filter((m) => {
    if (vendor && m.vendor !== vendor) return false;
    if (weightAccess && m.weight_access !== weightAccess) return false;
    if (freeOnly && !m.is_free) return false;
    if (!q) return true;
    const hay = `${m.vendor} ${m.name} ${m.id} ${m.display_name ?? ''}`.toLowerCase();
    return hay.includes(q);
  });
}

export function sortCatalogModels(
  models: CatalogModel[],
  key: CatalogSortKey,
  direction: 'asc' | 'desc',
): CatalogModel[] {
  const dir = direction === 'asc' ? 1 : -1;
  const sorted = [...models];
  sorted.sort((a, b) => {
    let cmp = 0;
    switch (key) {
      case 'vendor':
        cmp = a.vendor.localeCompare(b.vendor) || a.name.localeCompare(b.name);
        break;
      case 'name':
        cmp = a.name.localeCompare(b.name);
        break;
      case 'context':
        cmp = (a.context_tokens ?? -1) - (b.context_tokens ?? -1);
        break;
      case 'input_price':
        cmp = (a.api_input_per_million ?? Infinity) - (b.api_input_per_million ?? Infinity);
        break;
      case 'output_price':
        cmp = (a.api_output_per_million ?? Infinity) - (b.api_output_per_million ?? Infinity);
        break;
    }
    return cmp * dir;
  });
  return sorted;
}

export function paginateCatalog<T>(items: T[], page: number, pageSize: number): T[] {
  const start = (page - 1) * pageSize;
  return items.slice(start, start + pageSize);
}
