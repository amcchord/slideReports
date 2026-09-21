# Recipes modernization

This update brings setup and the application shell toward Slide's native visual language: Archivo, restrained light/dark surfaces, a compact setup card, familiar sidebar, and a link back to Recipes. It also fixes the initial collapsed-sidebar script accessing document.body before the body exists.

The Slide client now bounds reads to three attempts, respects short Retry-After delays, and applies connect/read timeouts. Mutations are not retried. Pagination copies caller parameters, follows full pages when next_offset is omitted, rejects malformed data/nonadvancing offsets, and uses API-side backup/snapshot time filters and matching sort order. Audit reads have both a lower date filter and a fixed upper timestamp so new audit entries do not move the paging window. Naive UTC datetimes from background sync are normalized to RFC3339. Existing invalid-key handling remains in place.

Sync storage now commits batches of 500 records instead of opening and committing a transaction for every row, and progress is emitted after committed batches. The upsert keeps unknown-field filtering and nested JSON behavior without mutating caller data. Batch rollback and sync progress are covered by two additional tests (nine focused tests total). A local 2,000-audit fixture benchmark measured 1.1776s for the previous per-row path and 0.0204s for four batches: 57.7× faster storage, excluding API fetch time. This is a synthetic local benchmark, not production end-to-end sync latency.

Embedded API key literals have been removed from source, documentation, and integration-test defaults. The special hardcoded-key auto-login exception has been removed; an existing session must disconnect before switching accounts. Legacy URL-key login remains compatible for sessions without a key; prefer the password form because URL credentials can enter browser/server history. This change does not rotate tokens or rewrite Git history.

Run the new focused tests:

```sh
python -m unittest discover -s tests -v
```

Seven tests cover retry limits, Retry-After, no mutation retry, missing pagination metadata, invalid collection payloads, repeated offsets, and RFC3339 date filters with a stable audit cutoff. Integration tests require `TEST_SLIDE_API_KEY`; there is no credential fallback.

Browser validation used a local isolated database and encryption/session configuration, with Demo key setup and dashboard checks. The updated client and batched storage completed a seven-day sync (3 devices, 7 agents, 257 backups, 490 snapshots, 2 clients, 113 alerts, 0 VMs) without errors; a separate audit read verified a five-minute server-filtered window. A subsequent 90-day sync completed all 13 data sources without errors, including 376 backups, 6,301 snapshots, and incremental audits. No email provider or scheduler was enabled and no paid AI call or report delivery was performed. Validate sync, report/PDF generation, and delivery with configured providers before rollout. Preserve production data, encryption key, session key, and scheduler configuration; do not accidentally start a second scheduler. No database migration or production deployment was performed.
