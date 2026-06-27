<script lang="ts">
  import { onMount } from 'svelte';
  import { assessFreshness, type FreshnessAssessment } from '../lib/data_freshness';

  interface SourceStatus {
    id: string;
    label: string;
    ok: boolean | null;
    detail?: string;
    workflowUrl: string;
  }

  interface Props {
    generatedAt?: string | null;
    staleWarning?: string | null;
    sources?: SourceStatus[];
    repoLabel?: string;
  }

  let {
    generatedAt = null,
    staleWarning = null,
    sources = [],
    repoLabel = 'pipeline',
  }: Props = $props();

  let freshness: FreshnessAssessment = $state(assessFreshness(generatedAt));
  let nowLabel = $state('');

  onMount(() => {
    freshness = assessFreshness(generatedAt);
    nowLabel = new Date().toISOString();
  });

  function sourceBadge(ok: boolean | null): string {
    if (ok === true) return 'ok';
    if (ok === false) return 'fail';
    return 'unknown';
  }
</script>

<details class="debug-panel card">
  <summary class="debug-summary">
    Data debug &amp; refresh
    <span class={`freshness-badge freshness-badge--${freshness.status}`}>{freshness.status}</span>
  </summary>

  <div class="debug-body">
    <dl class="debug-meta mono">
      <div>
        <dt>Build snapshot</dt>
        <dd>{generatedAt ?? '— missing —'}</dd>
      </div>
      <div>
        <dt>Page loaded (UTC)</dt>
        <dd>{nowLabel || '…'}</dd>
      </div>
      <div>
        <dt>Freshness</dt>
        <dd class={`freshness-text freshness-text--${freshness.status}`}>{freshness.label}</dd>
      </div>
    </dl>

    {#if staleWarning}
      <p class="debug-warn" role="status">{staleWarning}</p>
    {/if}

    <p class="debug-hint">
      Force-fetch runs in GitHub Actions (not in the browser). Each button opens the workflow to run manually.
    </p>

    <div class="debug-sources">
      {#each sources as src}
        <div class="source-row">
          <span class={`src-pill src-pill--${sourceBadge(src.ok)}`}>{sourceBadge(src.ok)}</span>
          <span class="source-label">{src.label}</span>
          {#if src.detail}<span class="source-detail mono">{src.detail}</span>{/if}
          <a class="btn btn-sm debug-btn" href={src.workflowUrl} target="_blank" rel="noopener">
            Force fetch
          </a>
        </div>
      {/each}
    </div>
  </div>
</details>

<style>
  .debug-panel {
    margin: 12px 0;
    padding: 0;
    overflow: hidden;
  }
  .debug-summary {
    cursor: pointer;
    padding: 10px 14px;
    font-size: 0.88rem;
    font-weight: 600;
    list-style: none;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .debug-summary::-webkit-details-marker { display: none; }
  .debug-body { padding: 0 14px 14px; }
  .debug-meta {
    display: grid;
    gap: 6px;
    font-size: 0.72rem;
    margin-bottom: 10px;
  }
  .debug-meta dt { color: var(--muted); display: inline; }
  .debug-meta dd { display: inline; margin: 0 0 0 4px; }
  .debug-warn {
    font-size: 0.82rem;
    padding: 8px 10px;
    border-radius: 6px;
    background: rgba(179, 49, 48, 0.12);
    border: 1px solid rgba(179, 49, 48, 0.35);
    margin-bottom: 10px;
  }
  .debug-hint {
    font-size: 0.78rem;
    color: var(--muted);
    margin-bottom: 10px;
  }
  .debug-sources { display: grid; gap: 8px; }
  .source-row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
    font-size: 0.8rem;
  }
  .source-label { font-weight: 500; }
  .source-detail { font-size: 0.7rem; color: var(--muted); }
  .src-pill {
    font-size: 0.65rem;
    text-transform: uppercase;
    padding: 2px 6px;
    border-radius: 4px;
    font-weight: 600;
  }
  .src-pill--ok { background: rgba(70, 113, 163, 0.2); color: var(--success); }
  .src-pill--fail { background: rgba(179, 49, 48, 0.2); color: var(--error); }
  .src-pill--unknown { background: rgba(122, 144, 168, 0.2); color: var(--muted); }
  .freshness-badge {
    font-size: 0.65rem;
    text-transform: uppercase;
    padding: 2px 6px;
    border-radius: 4px;
    margin-left: auto;
  }
  .freshness-badge--fresh { background: rgba(70, 113, 163, 0.2); }
  .freshness-badge--stale { background: rgba(229, 168, 50, 0.25); color: var(--warning); }
  .freshness-badge--missing { background: rgba(179, 49, 48, 0.2); color: var(--error); }
  .freshness-text--stale { color: var(--warning); }
  .freshness-text--missing { color: var(--error); }
  .debug-btn {
    margin-left: auto;
    font-size: 0.72rem;
    padding: 4px 10px;
  }
  @media (max-width: 640px) {
    .source-row { flex-direction: column; align-items: flex-start; }
    .debug-btn { margin-left: 0; }
  }
</style>
