# Explicitly registered Java static facts

`scripts/generate_source_facts.py` is an offline maintenance script producing a Source catalog accepted by the CLI and arguments accepted by `springboot_detect_drift`. It adds no MCP tools, endpoints, or Python runtime dependencies; the MCP process still does not scan the workspace.

## Execution and outputs

Requires a full JDK (`java`, `javac`) and the locked Python environment from the [validation workflow](launch/README.md). Register project-relative `.java` files with repeated `--source` arguments; no recursive scan or glob expansion occurs. `contextId` must come from an operator-verified runtime report; the script does not infer it.

```bash
uv run --no-sync python scripts/generate_source_facts.py \
  --project-root /absolute/project \
  --source src/main/java/example/Service.java \
  --source src/main/java/example/Configuration.java \
  --context-id application --target-id local \
  --output-dir /tmp/project-source-facts-new
```

The output directory must not exist. It contains:

- `source-catalog.json`: types/producers checked by the existing loader. Unknown implementations remain null; factory implementations and runtime proxy types are not guessed.
- `drift-arguments.json`: generated only when recognized Beans or routes exist, and checked by the existing drift validator. Omit unidentified dimensions; do not generate this file when neither is recognized. Empty arrays must not fabricate complete empty expectations.
- `source-facts-report.json`: always partial, recording fixed gaps, registered-file SHA-256, and uncollected runtime identity. It is neither catalog content nor a tool envelope.

Bean expectations use recognized names and the specified Context only. A declared interface return type does not establish runtime type, so no type-equality constraint is generated. `expectedScopeComplete` stays false, preventing objects outside the registered scope from being classified as extra runtime Beans/routes. Source declarations are caller expectations, not proof of conditional creation or route registration. Review generated results before sending arguments to MCP tools.

## Supported static subset

The script compiles the bundled [JDK helper](../scripts/java/SourceFacts.java) in a minimal environment and uses `JavacTask.parse()` on temporary byte snapshots of registered files. It performs no symbol analysis or target compilation, runs no target main/static initializer/annotation processor, and reads no target classpath, POM, or network. Successful parsing does not prove Java compilation succeeds.

Supported declarations are ordinary top-level classes/interfaces, explicitly resolvable parent types, standard `@Bean` methods in standard `@Configuration`, and supported literal mappings in standard Controllers. Resolve names only from registered declarations, explicit unambiguous imports, limited java.lang types, and supported fully qualified names. `@Bean` names/aliases must be literals; default names follow standard Bean method names.

Direct parents describe explicit extends/implements only; no explicit parent can produce an empty array. If any parent is unknown, omit the whole type and record a gap. Never replace unknown parents with an empty array. Wildcard imports, generics, nested/record/enum types, dynamic names, custom meta-annotations, overload/name conflicts, unresolved shadowing, and complex mappings are skipped or leave gaps. Unsupported declarations do not establish runtime absence.

Routes support recognized positive literal paths and explicit methods only. Extra conditions, unknown annotations, inheritance, or multiple mappings on one method cannot produce definite routes. Static summaries exclude source bodies, comments, method-body literals, and free text.

## Registering condition sources

By default, `conditionSources=[]` and the report includes `CONDITION_SOURCES_UNBOUND`. The script never constructs condition source keys from Bean names. For condition-chain correlation, explicitly register a JSON mapping with `--condition-sources relative/bindings.json`:

```json
{
  "example.StripeConfiguration#stripeClient": ["StripeConfiguration#stripeClient"]
}
```

Left-hand keys identify recognized configuration classes and factory methods; right-hand values must come from verified target condition reports. Unmatched keys fail rather than silently accepting typos. These remain operator declarations without network verification. Save the JSON as project-local `relative/bindings.json` and register it through the argument. See [Source catalog](source-catalog.md) for correlation boundaries.

## Limits and failures

Register at most 256 files, 256 KiB per file and 2 MiB total. The helper emits at most 1,000 facts; the catalog retains its 256 KiB/1,000-entry limits and drift expectations their 100-entity limit. Narrow registration on overflow; do not silently paginate or truncate into an apparently complete set.

Read through directory descriptors and `O_NOFOLLOW`, rejecting symlinks, escaping paths, nonregular files, and changes during reads. These safety interfaces require platform support. Individual file samples are not an atomic repository snapshot. Generated strings pass existing SanitizerPipeline string rules and an independent output gate; unsafe output fails instead of changing identifiers to invent associations.

Failure exits 2 with fixed classifications on stderr, never compiler diagnostics, source, or stacks; success exits 0. Validate before atomically moving the temporary output directory; never overwrite existing results. See [local build evidence](build-evidence.md) for the distinction between build artifacts and running identity.
