# Response normalization and relationship analysis

Normalization processes Actuator/OpenAPI JSON accepted by fixed HTTP gates. See [security architecture](security-and-sanitization.md) for actual endpoints and boundaries; the [Schema](../../src/spring_runtime_mcp/schemas/tools-contract.json) defines fields.

## Inputs and version evidence

ResponseGateReader accepts ordinary JSON and Actuator v2/v3 media types, constructing ParsedObservation with target, snapshot, observation, observedAt, and endpoint identities. Adapters read Contexts and domain data from reported structures; exact Boot version is null without evidence. Online calls read required fixed endpoints without automatic capability handshakes, version probing, or multi-path fallback.

| Domain | Normalization behavior |
| --- | --- |
| beans | Parse contexts/beans, types, scope, aliases, and dependencies to establish Context/Bean identities and the visible dependency graph. |
| conditions | Read positiveMatches/negativeMatches, recognize bounded known condition messages, and normalize outcome; preserve gaps for unknown syntax. |
| mappings | Extract paths, methods, handlers, Contexts, and stacks from MVC dispatchers, WebFlux annotations, and recognizable functional routes. |
| health | Traverse visible components/details; distinguish aggregate status, hidden details, unreadable state, and tree-depth limits. |
| flyway/liquibase | Read each engine's reported inventory and Context/migration-Bean identity; project versions, changeSets, checksums, order, and state. |
| startup | Parse timeline/events identities, parents, and durations; filter slow steps and include ancestor chains. |
| env/configprops | Normalize sources, bindings, and effective values within registered policy; configuration is disabled and values hidden by default. |
| openapi | Recognize supported document structures, project operations or Schemas, and resolve bounded in-document references. |

Synthetic tests and some isolated samples cover Boot 2.7/3.x/4.x-related shapes and MVC/WebFlux. Exact versions and client combinations require separate acceptance; recognizing a structure does not establish a complete compatibility matrix.

## Bean graphs and Context visibility

Bean identity includes target, Context, canonicalName, and beanKind. Each Context builds bidirectional canonicalName/alias indices; name conflicts stay unresolved. Resolve dependencies in the current Context first, then follow parentId upward. Child Beans shadow same-named ancestors; parents do not resolve dependencies downward into children.

Build the full visible graph and reverse index before filtering/pagination, supporting multi-hop traversal in both directions. Cycles, missing parents, unexposed dependencies, ambiguous aliases, and visit budgets produce gaps. Retain usable facts and mark incompleteness when depth/node limits are reached.

The Source catalog provides operator-verified type inheritance and producer facts only. Correlate runtime Beans with catalog producers using Context, name/aliases, type, source keys, and other evidence. An unscanned type cannot be represented as a scanned empty inheritance list; a missing catalog cannot establish Bean absence. See the [catalog guide](../source-catalog.md) for format and limits.

## Conditions and blocking chains

Evaluate AnyNestedCondition, AllNestedConditions, and NoneNestedConditions recursively using three-valued ANY/ALL/NONE results. Reported outcomes, recognized syntax, search scope, and source-producer associations jointly constrain attribution. Conflicts, truncation, and unknown implementations remain unknown.

ConditionalOnBean supports currently recognizable types and strictly matching single-name missing messages. Recognize `did not find any beans named <name>` for a single names selector only when the suffix exactly matches that selector. Compound requirements, mismatched names, or nonunique resolution cannot produce a definite chain. MissingBean uses the inverse condition direction.

Evidence-backed blocking paths may follow `REQUIRED_BEAN_MISSING → SOURCE_FACTORY_NOT_CREATED → PROPERTY_NOT_FOUND/PROPERTY_VALUE_MISMATCH`. Cross-layer correlation requires a unique catalog producer and exact conditionSources. An outer result can remain partial despite a known local condition. Keep runtime-proxy and source-declared types separate; never invent types or factory relationships to fill gaps.

## Routes, health, migrations, and startup

MVC/WebFlux registration facts come from mappings, without business-URL requests. Functional predicates support only recognized positive combinations and media constraints; OR/NOT/unknown syntax preserve gaps. If a non-DispatcherServlet such as Jersey may cover the requested path, empty dispatcher results include NON_DISPATCHER_SERVLET_ROUTES_UNOBSERVED and an unknown total.

Preserve overall health and visible child components separately. Unreadable components, missing status, or detail/depth restrictions produce partial results. Gaps affecting filtered counts make totalMatched null. A fixed health probe's 503 is parseable evidence; connection success alone does not mean healthy.

Sort migrations using engine-reported installation order and stable identities, retaining null/UNKNOWN for missing fields. Flyway version expectations use the latest successful versioned record in installation order. Liquibase has no equivalent standard version semantics; explicitly report unsupported version expectations. Never invent unreported pending state, duration, or failure; MARK_RAN expresses only engine-reported state.

Startup timelines retain units, events, parent chains, and truncation evidence. Missing parents, non-tree relationships, or depth/node limits produce partial results. Do not sum overlapping durations into total JVM startup time. The target must configure BufferingApplicationStartup before run; see [target setup](../target-app-setup.md).

## OpenAPI references

Online reads use fixed `/actuator/openapi`; supported versions/dialects follow the existing parser. In-document JSON Pointers handle `~0`/`~1` escapes. Reference expansion defaults to two levels and allows at most eight. Shared references are projected independently within visit and output budgets.

Retain traceable facts from direct and second-level references. Record gaps for cycles, unresolved or remote references, and uncertain dialects or levels; remote `$ref` is never fetched. Nonconflicting PathItem siblings may be retained. If conflicts or unreadable operations affect complete counts, totalMatched is null.

Handle a business Schema property named description separately from raw descriptive free text. Projection retains permitted structural fields while always applying sanitization and the output gate.

## Drift and evidence strength

Drift compares only caller-supplied dimensions. An omitted array means no comparison; an explicit empty array means an empty expectation. Extra runtime objects can be established only with expectedScopeComplete=true and complete runtime evidence. Bean graphs may propagate impact; sourceRevision/sourceModifiedAt are caller declarations.

Insufficient version, time, Context, instance, or startup evidence remains candidate/unknown. A newer source file alone does not prove that the process was not restarted. Recipes/errors come only from local safe templates; an HTTP status alone cannot establish a collection, configuration, or business root cause.
