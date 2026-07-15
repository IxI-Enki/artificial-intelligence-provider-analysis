import { describe, expect, it } from 'vitest';
import {
  filterCatalogModels,
  paginateCatalog,
  sortCatalogModels,
  type CatalogModel,
} from '../src/lib/catalog_logic';

const sample: CatalogModel[] = [
  {
    id: 'openai/gpt-4.1',
    vendor: 'openai',
    name: 'GPT-4.1',
    context_tokens: 1_000_000,
    api_input_per_million: 2,
    api_output_per_million: 8,
    weight_access: 'closed',
    is_free: false,
  },
  {
    id: 'meta-llama/llama-4-maverick',
    vendor: 'meta-llama',
    name: 'Llama 4 Maverick',
    context_tokens: 1_048_576,
    api_input_per_million: 0.2,
    api_output_per_million: 0.8,
    weight_access: 'open',
    is_free: false,
  },
  {
    id: 'meta-llama/llama-free',
    vendor: 'meta-llama',
    name: 'Llama Free',
    context_tokens: 8000,
    api_input_per_million: 0,
    api_output_per_million: 0,
    weight_access: 'open',
    is_free: true,
  },
];

describe('filterCatalogModels', () => {
  it('filters by vendor and weight access', () => {
    const open = filterCatalogModels(sample, '', 'open', false, '');
    expect(open).toHaveLength(2);
    const meta = filterCatalogModels(sample, 'meta-llama', '', false, '');
    expect(meta).toHaveLength(2);
  });

  it('filters free models and search query', () => {
    const free = filterCatalogModels(sample, '', '', true, '');
    expect(free).toHaveLength(1);
    const gpt = filterCatalogModels(sample, '', '', false, 'gpt-4');
    expect(gpt).toHaveLength(1);
  });
});

describe('sortCatalogModels', () => {
  it('sorts by context descending', () => {
    const sorted = sortCatalogModels(sample, 'context', 'desc');
    expect(sorted[0].id).toBe('meta-llama/llama-4-maverick');
  });
});

describe('paginateCatalog', () => {
  it('returns page slice', () => {
    expect(paginateCatalog(sample, 1, 2)).toHaveLength(2);
    expect(paginateCatalog(sample, 2, 2)).toHaveLength(1);
  });
});
