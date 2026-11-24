# JVM thread diagnostics

## MCP tool

Start the local host with `--enable-thread-diagnostics` to register
`springboot_analyze_threads`. The target must already expose and authorize
the JSON `GET /actuator/threaddump` on its registered loopback origin. The
default host registers eight tools. Enabling the option adds the thread tool
for the lifetime of the process. Listing either configuration makes no target
requests.

The input accepts only `targetId`, `maxResults` (1–50, default 50), and
`cursor`. The result reports observed state counts, cycle and chain counts,
and a page of `data.items` with cycles first. Each item includes up to 16
ordered thread IDs. Cycle items include the full observed cycle length and
`containsTimedWait`. A cycle containing a timed wait is a snapshot clue.
An observed cycle without timed waits supports a possible deadlock finding.
Chain items identify whether the chain ended, entered a cycle, reached an
unobserved owner, or hit the path depth limit.

The tool establishes relationships before pagination and reads the dump
once on the initial query. Continue with the original arguments and
`nextCursor` to reuse the sanitized snapshot. Missing evidence produces
coverage gaps and an unknown total when relevant. The result scope is limited
to the platform threads reported by the dump. Both MCP result representations
fit the complete 16,384-byte frame cap.

## Local JVM acceptance

Run the `jvm-threads` case in the [runtime benchmark matrix](runtime-benchmarks.md).
It checks the tool against real loopback Actuator responses from an isolated
Boot 3.4.8 / JDK 21 fixture, including a JVM-confirmed monitor deadlock,
single-read continuation, and recovery from a timed lock cycle.

## Offline file replay

From the source checkout, pass a local JSON file matching the Actuator
`threads` response shape. The script uses bounded file and JSON readers and
works with synthetic fixtures.

```bash
uv run --no-sync python scripts/analyze_thread_dump.py /path/to/threads.json
```

The summary counts observed thread states and follows positive
`lockOwnerId` values from blocked or waiting threads. Closed cycles in the
reported owner graph are evidence of a possible deadlock. A single blocked
thread can have a finite wait chain. Missing owners, malformed rows,
duplicate thread IDs, and unrecognized states produce coverage gaps.
`waitCycleStatus` is `unknown` when missing evidence prevents a conclusion
and no cycle was observed. `noneObserved` applies to this snapshot only.

The graph is analyzed before projection. The output keeps up to eight cycle
records and eight chain records, with up to 16 IDs per record. Cycle length
and record counts describe the observed graph before truncation. The script
emits thread IDs as strings and projects only counts, IDs, and fixed labels.
Thread names, lock names, and stack frames are excluded.

The replay script consumes a JSON file from disk. Network reads and thread dump
collection are outside its interface. For the input fields, see the
[Spring Boot Thread Dump API](https://docs.spring.io/spring-boot/3.4/api/rest/actuator/threaddump.html).
