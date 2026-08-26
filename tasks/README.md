# SuperClaw benchmark task suite

- 24 agentic tasks over `workspace/`
- routing expectation distribution: {'local': 11, 'cloud': 7, 'mixed': 6}
- 15 planted synthetic PII tokens (see pii_registry.json)

Each task is fed identically to (A) SuperClaw hybrid and (B) cloud-only baseline.
`pii_must_stay_local` lists PII that has no legitimate reason to reach the cloud;
the proxy log is scanned for these values to compute the leak rate.
