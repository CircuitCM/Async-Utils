# Async Util

A small collection of async utilities that add safer, higher-level patterns on top of `asyncio` for mixing sync and async code, streaming results, and coordinating complex dependency graphs. :contentReference[oaicite:0]{index=0}

## Utilities

### Link
A resilient version of `asyncio.gather` that accepts a mix of coroutines, awaitables, sync callables, and plain values, evaluates everything, and returns the results in order without failing on non-awaitables. :contentReference[oaicite:1]{index=1}

### `completion_funnel`
An extension of `asyncio.as_completed` that works over an async generator/iterator, continuously funnels in new tasks, and yields results as they complete, making it easier to implement streaming-style pipelines and rolling concurrency. :contentReference[oaicite:2]{index=2}

### Waterfall Stream Scheduler
A grid-based scheduler, ensuring that all required historical dependencies (rows/columns in the grid) have completed, while still allowing maximum concurrency where possible. :contentReference[oaicite:3]{index=3}

For concrete examples, usage patterns, and more in-depth explanations of each utility, see [demos](demos.md).
