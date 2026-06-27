<script lang="ts">
  import { onMount } from 'svelte';
  import { filterProviders } from '../lib/filter_logic';

  export let providers: Array<Record<string, unknown>> = [];

  let deploymentFilter = '';
  let categoryFilter = '';
  let empty = false;
  let mounted = false;

  $: filtered = filterProviders(
    providers as Parameters<typeof filterProviders>[0],
    deploymentFilter,
    categoryFilter,
  );
  $: empty = filtered.length === 0 && (deploymentFilter !== '' || categoryFilter !== '');

  function reset() {
    deploymentFilter = '';
    categoryFilter = '';
  }

  function applyVisibility() {
    if (!mounted) return;
    const ids = new Set(filtered.map((p) => p.id));
    document.querySelectorAll<HTMLElement>('.provider-card').forEach((el) => {
      const id = el.dataset.providerId;
      el.style.display = id && ids.has(id) ? '' : 'none';
    });
  }

  onMount(() => {
    mounted = true;
    applyVisibility();
  });

  $: if (mounted) filtered, applyVisibility();
</script>

<div class="filter-bar card" style="padding:12px 16px;margin-bottom:12px">
  <div style="display:flex;flex-wrap:wrap;gap:12px;align-items:end">
    <label>
      <span class="mono" style="font-size:.7rem;display:block;margin-bottom:4px">Deployment</span>
      <select bind:value={deploymentFilter} style="padding:6px 8px;border-radius:6px">
        <option value="">All</option>
        <option value="api">API</option>
        <option value="self_hosted">Self-hosted</option>
        <option value="both">Both</option>
      </select>
    </label>
    <label>
      <span class="mono" style="font-size:.7rem;display:block;margin-bottom:4px">Category</span>
      <select bind:value={categoryFilter} style="padding:6px 8px;border-radius:6px">
        <option value="">All</option>
        <option value="chat">Chat</option>
        <option value="embedding">Embedding</option>
        <option value="multimodal">Multimodal</option>
      </select>
    </label>
    {#if empty}
      <div style="flex:1 1 100%;color:var(--muted);font-size:.88rem">
        No providers match the current filters.
        <button type="button" on:click={reset} style="margin-left:8px;padding:4px 10px;border-radius:6px;cursor:pointer">Reset filters</button>
      </div>
    {/if}
  </div>
</div>
