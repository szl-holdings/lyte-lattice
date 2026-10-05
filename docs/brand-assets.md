<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- contract: lyte.brand-assets/v1 -->

# Brand asset maintenance

DECLARED application contract for `scripts/brand-check.mjs` and
`scripts/write-atomic.mjs`. Lyte's identity is configured in
`src/lib/og/site.json`. This documentation belongs to the application repository
and is checked by its offline test suite.

## Optional background generation

Do not wait for optional brand generation before completing unrelated checks or
reporting completed application work. Report unfinished brand assets explicitly.
A generation task creates `.grok/og-pending` under the application root and removes
it when finished. The marker expires after 10 minutes, so an interrupted task
cannot suppress brand warnings indefinitely. The CLI self-check reports the marker
but still judges the asset files; the marker never establishes a successful result.

## Self-check

Run these commands from the application root, choosing the check that matches the
surface. A custom card is `public/og.jpg` (legacy `public/og.png` is recognized),
with `"card": "custom"` in `src/lib/og/site.json`. Keep each card at or below
600 KiB. For the normal custom-card check:

```sh
node scripts/brand-check.mjs
```

A game requires a custom card, `"type": "x:game"`, and a 1200-by-264 JPEG at
`public/x-banner.jpg`, also at or below 600 KiB. Use this check only for a game:

```sh
node scripts/brand-check.mjs --game
```

A plain utility intentionally keeping its placeholder can use:

```sh
node scripts/brand-check.mjs --placeholder-ok
```

The placeholder flag does not excuse a missing game card. A failed self-check is
reported as a failure; missing generation tooling is reported as unavailable.

## Atomic handover

Stage complete files under `.grok/` on the same filesystem as the application.
Keep staging files outside `public/`, which Vite copies into the built application.
After generating and validating each complete file, use the corresponding handover:

```sh
node scripts/write-atomic.mjs .grok/og.jpg.tmp public/og.jpg
node scripts/write-atomic.mjs .grok/x-banner.jpg.tmp public/x-banner.jpg
node scripts/write-atomic.mjs .grok/site.json.tmp src/lib/og/site.json
```

Relative paths resolve from the script's application root. Handover uses a rename
within one filesystem. Readers see the existing file or its complete replacement;
an interrupted generation leaves the existing target intact. Cross-filesystem
handover fails instead of copying into a public staging file. Run the appropriate
self-check after handover, then remove the pending marker when the task finishes.
