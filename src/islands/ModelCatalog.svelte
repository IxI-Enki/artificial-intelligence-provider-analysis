<script lang="ts">
  import {
    filterCatalogModels,
    paginateCatalog,
    sortCatalogModels,
    type CatalogModel,
    type CatalogSortKey,
  } from '../lib/catalog_logic';

  export let models: CatalogModel[] = [];
  export let vendors: string[] = [];
  export let generatedAt = '';

  let vendorFilter = '';
  let weightFilter = '';
  let freeOnly = false;
  let query = '';
  let sortKey: CatalogSortKey = 'context';
  let direction: 'asc' | 'desc' = 'desc';
  let page = 1;
  const pageSize = 50;

  $: filtered = filterCatalogModels(models, vendorFilter, weightFilter, freeOnly, query);
  $: sorted = sortCatalogModels(filtered, sortKey, direction);
  $: pageCount = Math.max(1, Math.ceil(sorted.length / pageSize));
  $: safePage = Math.min(page, pageCount);
  $: pageRows = paginateCatalog(sorted, safePage, pageSize);
  $: if (page > pageCount) page = pageCount;

  function fmtNum(v: number | null | undefined): string {
    if (v === null || v === undefined) return 'n/a';
    return v.toLocaleString('en-US');
  }

  function fmtUsd(v: number | null | undefined): string {
    if (v === null || v === undefined) return 'n/a';
    if (v === 0) return '$0';
    return '$' + v.toFixed(v < 1 ? 4 : 2);
  }

  function resetFilters() {
    vendorFilter = '';
    weightFilter = '';
    freeOnly = false;
    query = '';
    page = 1;
  }
</script>

<div class="catalog-toolbar card" style="padding:12px 16px;margin-bottom:12px">
  <div class="catalog-toolbar-grid">
    <label>
      <span class="mono toolbar-label">Vendor</span>
      <select bind:value={vendorFilter} on:change={() => (page = 1)}>
        <option value="">All ({vendors.length})</option>
        {#each vendors as vendor}
          <option value={vendor}>{vendor}</option>
        {/each}
      </select>
    </label>
    <label>
      <span class="mono toolbar-label">Weights</span>
      <select bind:value={weightFilter} on:change={() => (page = 1)}>
        <option value="">All</option>
        <option value="open">Open (HF linked)</option>
        <option value="closed">Closed API</option>
        <option value="unknown">Unknown</option>
      </select>
    </label>
    <label>
      <span class="mono toolbar-label">Sort</span>
      <select bind:value={sortKey} on:change={() => (page = 1)}>
        <option value="context">Context</option>
        <option value="input_price">Input price</option>
        <option value="output_price">Output price</option>
        <option value="vendor">Vendor</option>
        <option value="name">Name</option>
      </select>
    </label>
    <label>
      <span class="mono toolbar-label">Direction</span>
      <select bind:value={direction} on:change={() => (page = 1)}>
        <option value="desc">High to low</option>
        <option value="asc">Low to high</option>
      </select>
    </label>
    <label class="catalog-search">
      <span class="mono toolbar-label">Search</span>
      <input
        type="search"
        placeholder="Model name or id"
        bind:value={query}
        on:input={() => (page = 1)}
      />
    </label>
    <label class="catalog-free">
      <input type="checkbox" bind:checked={freeOnly} on:change={() => (page = 1)} />
      <span>Free only</span>
    </label>
    <button type="button" class="catalog-reset" on:click={resetFilters}>Reset</button>
  </div>
  <p class="catalog-meta mono">
    {sorted.length} models · page {safePage}/{pageCount}
    {#if generatedAt}
      · snapshot {new Date(generatedAt).toLocaleString('en-GB', { timeZone: 'UTC' })} UTC
    {/if}
  </p>
</div>

<div class="card catalog-table-wrap">
  <table class="data catalog-table">
    <thead>
      <tr>
        <th>Vendor</th>
        <th>Model</th>
        <th>Context</th>
        <th>In / 1M</th>
        <th>Out / 1M</th>
        <th>Weights</th>
        <th>Tools</th>
        <th>Modality</th>
      </tr>
    </thead>
    <tbody>
      {#each pageRows as model (model.id)}
        <tr>
          <td class="mono">{model.vendor}</td>
          <td>
            <strong>{model.name}</strong>
            <span class="mono catalog-slug">{model.id}</span>
            {#if model.description}
              <span class="catalog-desc">{model.description}</span>
            {/if}
          </td>
          <td class="mono">{fmtNum(model.context_tokens)}</td>
          <td class="mono">{fmtUsd(model.api_input_per_million)}</td>
          <td class="mono">{fmtUsd(model.api_output_per_million)}</td>
          <td>
            <span class="weight-badge weight-{model.weight_access}">{model.weight_access}</span>
            {#if model.hugging_face_id}
              <span class="mono catalog-hf">{model.hugging_face_id}</span>
            {/if}
          </td>
          <td class="mono">
            {model.supports_tools ? 'yes' : 'no'}
            {#if model.supports_structured_outputs}
              <span class="catalog-tag">json</span>
            {/if}
          </td>
          <td class="mono">{model.modality ?? 'n/a'}</td>
        </tr>
      {:else}
        <tr>
          <td colspan="8">No models match the current filters.</td>
        </tr>
      {/each}
    </tbody>
  </table>
</div>

{#if pageCount > 1}
  <div class="catalog-pager">
    <button type="button" disabled={safePage <= 1} on:click={() => (page = safePage - 1)}>
      Previous
    </button>
    <span class="mono">Page {safePage} of {pageCount}</span>
    <button type="button" disabled={safePage >= pageCount} on:click={() => (page = safePage + 1)}>
      Next
    </button>
  </div>
{/if}

<style>
  .catalog-toolbar-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 12px;
    align-items: end;
  }
  .toolbar-label {
    font-size: 0.7rem;
    display: block;
    margin-bottom: 4px;
    color: var(--muted);
  }
  select,
  input[type='search'] {
    width: 100%;
    padding: 6px 8px;
    border-radius: 6px;
    border: 1px solid var(--border);
    font: inherit;
  }
  .catalog-search {
    grid-column: span 2;
  }
  .catalog-free {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.85rem;
    padding-bottom: 6px;
  }
  .catalog-reset {
    padding: 7px 12px;
    border-radius: 6px;
    border: 1px solid var(--border);
    background: var(--surface);
    cursor: pointer;
    font: inherit;
  }
  .catalog-meta {
    margin: 10px 0 0;
    font-size: 0.75rem;
    color: var(--muted);
  }
  .catalog-table-wrap {
    overflow-x: auto;
  }
  .catalog-table td {
    vertical-align: top;
    font-size: 0.84rem;
  }
  .catalog-slug {
    display: block;
    font-size: 0.68rem;
    color: var(--muted);
    margin-top: 2px;
  }
  .catalog-desc {
    display: block;
    font-size: 0.75rem;
    color: var(--muted);
    margin-top: 4px;
    max-width: 42rem;
  }
  .catalog-hf {
    display: block;
    font-size: 0.65rem;
    color: var(--muted);
    margin-top: 2px;
  }
  .catalog-tag {
    display: inline-block;
    margin-left: 4px;
    padding: 1px 5px;
    border-radius: 4px;
    background: var(--surface);
    font-size: 0.65rem;
  }
  .weight-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 0.68rem;
    font-weight: 600;
    text-transform: uppercase;
  }
  .weight-open {
    background: color-mix(in srgb, var(--success) 12%, var(--bg));
    color: var(--success);
  }
  .weight-closed {
    background: color-mix(in srgb, var(--primary) 10%, var(--bg));
    color: var(--primary);
  }
  .weight-unknown {
    background: color-mix(in srgb, var(--muted) 15%, var(--bg));
    color: var(--muted);
  }
  .catalog-pager {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 16px;
    margin: 16px 0 8px;
  }
  .catalog-pager button {
    padding: 8px 14px;
    border-radius: 6px;
    border: 1px solid var(--border);
    background: var(--bg);
    cursor: pointer;
    font: inherit;
  }
  .catalog-pager button:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }
  @media (max-width: 720px) {
    .catalog-search {
      grid-column: span 1;
    }
  }
</style>
