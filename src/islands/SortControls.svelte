<script lang="ts">
  import { onMount } from 'svelte';
  import { sortProviders } from '../lib/filter_logic';

  export let providers: Array<Record<string, unknown>> = [];

  let sortKey: 'context' | 'price' = 'context';
  let direction: 'asc' | 'desc' = 'desc';
  let mounted = false;

  $: sorted = sortProviders(
    providers as Parameters<typeof sortProviders>[0],
    sortKey,
    direction,
  );

  function reorderDom() {
    if (!mounted) return;
    const grid = document.querySelector('.provider-grid');
    if (!grid) return;
    sorted.forEach((p) => {
      const el = grid.querySelector(`[data-provider-id="${p.id}"]`);
      if (el) grid.appendChild(el);
    });
  }

  onMount(() => {
    mounted = true;
    reorderDom();
  });

  $: if (mounted) sorted, reorderDom();
</script>

<div class="sort-controls card" style="padding:12px 16px;margin-bottom:12px">
  <div style="display:flex;flex-wrap:wrap;gap:12px;align-items:end">
    <label>
      <span class="mono" style="font-size:.7rem;display:block;margin-bottom:4px">Sort by</span>
      <select bind:value={sortKey} style="padding:6px 8px;border-radius:6px">
        <option value="context">Context window</option>
        <option value="price">Input price</option>
      </select>
    </label>
    <label>
      <span class="mono" style="font-size:.7rem;display:block;margin-bottom:4px">Direction</span>
      <select bind:value={direction} style="padding:6px 8px;border-radius:6px">
        <option value="desc">High to low</option>
        <option value="asc">Low to high</option>
      </select>
    </label>
  </div>
</div>
