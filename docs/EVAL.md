# Phase-5 – Reproducible Evaluation
> Generated: 2026-11-06T18:23:48.163382


## Scenarios


| Scenario | Cache | Fallback | Median latency (s) | P95 latency (s) | P99 latency (s) | RPS | Error % | Cache hit % | Fallback % | Cost / 1k requests |

|----------|-------|----------|-------------------|----------------|----------------|-----|---------|-------------|------------|-------------------|

| Cache OFF | OFF | **ON** | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |

| Cache ON | ON | **ON** | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |

| Fallback OFF | OFF | **OFF** | N/A | N/A | N/A | N/A | N/A | N/A | None / None | N/A |

| Fallback ON | OFF | **ON** | N/A | N/A | N/A | N/A | N/A | N/A | None / None | N/A |

| Hard-down | OFF | **OFF** | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
