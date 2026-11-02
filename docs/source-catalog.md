# Bean source catalogs and evidence boundaries

Context IDs preserve the exact text identity from runtime reports; hyphenated names such as `shop-product` can be registered.

Complete a basic query using the [first-query guide](first-query.md). A source catalog is an optional enhancement, not a prerequisite.

`--source-catalog` accepts operator-prepared JSON facts; it does not scan, execute, or download source.
Use the repository's [restricted static-fact generator](source-facts-generation.md) on explicitly registered Java files, or manually prepare a minimal subset from verified source. The generator handles a limited AST subset, not full Spring scanning; operators must review its output.
The [CLI](../src/spring_runtime_mcp/cli.py) loads the catalog at startup using the [existing loader](../src/spring_runtime_mcp/adapters/source_catalog.py). It is not a tool-call argument.

```bash
uv run --no-sync python -m spring_runtime_mcp.cli \
  --base-url http://127.0.0.1:18081 --target-id local \
  --token-env SHOP_ACTUATOR_TOKEN --source-catalog /abs/path/source-catalog.json
```

Credentials come from registered environment variables, not the catalog. Catalog `targetId` must match `--target-id`; the application still needs independently authorized beans/conditions access.

## Fields and correlation

Top-level fields are `targetId`, optional `sourceRevision`, `types`, and `producers` only. Files are capped at 262,144 bytes and 1,000 combined types/producers.
Each type requires `name` and `directSupertypes`. Each producer requires every field below:

| Field | Registration evidence |
| --- | --- |
| `contextId` | Exact beans/conditions Context ID; `shop-product` differs from `shop_product`. Text length 1–256, rejecting C0 (U+0000–U+001F) and DEL (U+007F); not validated as a Java type name. |
| `beanName`, `aliases` | Bean names/aliases verified from source; do not infer unverified registration names from class names. |
| `declaredType`, `implementationType` | Source-declared type and known implementation; use null for unknown implementations. Runtime proxy types differ from source implementation types. |
| `configurationClass`, `factoryMethod` | Actual configuration class/factory method; factoryMethod is null for nonfactory producers. |
| `conditionSources` | Array exactly matching conditions source keys; never concatenate from Bean names. Nested binary type names may contain `$` while condition keys may use `.`; verify separately. |
| `sourceFile`, `sourceLine` | File path relative to the authorized source snapshot and positive line number. Reject absolute paths, parent traversal, backslashes, and C0 controls. |

Symbol fields other than contextId retain bounded Java-symbol validation. Do not add `complete`, dependency edges, or custom condition-message fields.
`sourceRevision` is an operator declaration, not proof of the running version. The server does not reread files/lines to verify them. Keep source digests and catalog-coverage notes outside the repository.

Register verified direct parents only. Omit an unscanned type instead of using `directSupertypes: []` to represent unknown information.
There is no global scan-completeness field, so a catalog cannot establish whole-application completeness. Uncovered types, producers, and conditions remain unknown/partial.

## Assessing the enhancement

Repeat the same query against the same instance and compare visible facts and gaps, rather than counting partial results:

- For an existing Bean, add `producer` with `correlated` evidence only when Context, name/aliases, and actual type satisfy existing matching rules. CGLIB/source mismatches may still produce null; never invent proxy source facts to force correlation.
- For an uncreated Bean, correlate the source-expected producer with the conditions configuration class/method. The condition report is runtime evidence of matching; the catalog alone does not establish why creation failed.
- Recognized negative property conditions can yield `PROPERTY_NOT_FOUND` / `PROPERTY_VALUE_MISMATCH`. Unknown syntax remains unknown; other incomplete condition/graph evidence can leave the overall result partial despite a known local cause.
- Missing catalogs, insufficient condition permissions, or source-key/Context mismatches cannot turn empty items into proof of Bean absence. `totalMatched: null` means a complete matching count cannot be established.

Parse a single-name `ConditionalOnBean` negative message only when its suffix matches the unique names selector. Exact conditionSources and a unique catalog producer can correlate it with an upstream property condition. Missing catalogs, Context/source mismatches, unattributable compound requirements, or unreadable conditions remain unknown/partial. Recognized type selectors and transitive conditions use the same evidence chain; unknown syntax retains gaps.

Bean-name parsing and catalog Java type/source validation are separate. Bounded hyphenated names supported by condition messages do not imply all such names satisfy catalog symbol validation. All runtime-proxy/source-type combinations, arbitrary upstream messages, and the full Boot matrix remain unverified.

Loading a catalog does not remove graph depth/association limits, unexposed runtime dependencies, sensitive-identifier redaction, or unscanned type relationships.
See the [calling policy](contracts/tool-calling-policy.md) and [cross-version normalization](architecture/cross-version-normalization.md).
