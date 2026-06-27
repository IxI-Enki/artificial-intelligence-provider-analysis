import { describe, expect, it } from 'vitest';
import { filterProviders, sortProviders } from '../src/lib/filter_logic';

const sample = [
  {
    id: 'a',
    name: 'A',
    deployment_type: 'api' as const,
    model_category: 'chat',
    context_tokens: 100000,
    api_input_per_million: 2,
  },
  {
    id: 'b',
    name: 'B',
    deployment_type: 'both' as const,
    model_category: 'chat',
    context_tokens: 500000,
    api_input_per_million: 0.5,
  },
  {
    id: 'c',
    name: 'C',
    deployment_type: 'self_hosted' as const,
    model_category: 'embedding',
    context_tokens: 8000,
    api_input_per_million: null,
  },
];

describe('filterProviders', () => {
  it('filters by deployment_type', () => {
    const apiOnly = filterProviders(sample, 'api', '');
    expect(apiOnly.map((p) => p.id)).toEqual(['a', 'b']);
  });

  it('filters by model_category', () => {
    const chat = filterProviders(sample, '', 'chat');
    expect(chat).toHaveLength(2);
  });
});

describe('sortProviders', () => {
  it('sorts by context descending', () => {
    const sorted = sortProviders(sample, 'context', 'desc');
    expect(sorted[0].id).toBe('b');
  });
});
