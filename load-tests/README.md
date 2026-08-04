# CZ Virtual PLC k6 results

Production read-only load tests executed on 2026-08-04 against
`https://plc.tommy-huang.dev`. No login, write, runtime command or control endpoint was used.

| Profile | Max active VUs | Requests | Throughput | Error rate | p95 | p99 | Result |
|---|---:|---:|---:|---:|---:|---:|---|
| Smoke | 1 | 15 | 1.17 req/s | 0% | 1.92 s | — | Readiness slow |
| Baseline | 10 | 940 | 9.29 req/s | 0% | 199 ms | — | Pass |
| Breakpoint | 1,854 | 113,918 | 553.9 req/s | 1.11% | 1.26 s | 4.37 s | Auto-stopped |

The 200- and 500-VU stages were stable. Timeouts appeared around 1,000 VUs; the 1% error guard
stopped the ramp toward 2,000 at 1,854 active VUs. The run did not force the service to 5,000 VUs.

`/api/readyz` was measured only by smoke because it synchronously checks storage/GCS. Baseline and
breakpoint use `/` and lightweight `/api/livez`.

```bash
k6 run -e PROFILE=smoke load-tests/k6-readonly.js
k6 run -e PROFILE=baseline load-tests/k6-readonly.js
k6 run -e PROFILE=breakpoint load-tests/k6-readonly.js
```

Breakpoint is a production-impacting test. Run it only in an approved maintenance window with VM
and reverse-proxy monitoring visible. Raw metrics are in `results/2026-08-04.json`.
