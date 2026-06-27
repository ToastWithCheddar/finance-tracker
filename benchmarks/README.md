# 40-benchmarks — Performance benchmarking

All net-new perf harnesses and reports.

```
40-benchmarks/
├── backend/        # locust scenarios + pytest-benchmark microbenchmarks; reports under <git-sha>/
├── frontend/       # Lighthouse CI configs + bundle visualizer snapshots; reports under <git-sha>/
└── ml-worker/      # custom bench.py: latency, throughput, memory, cache hit rate
```

Reports are git-ignored except for the latest baseline + a small JSON summary checked in to track trends. See `docs/audit/improvement-sections/A-performance.md` and `F-ml-worker-revival.md` for harness specs.
