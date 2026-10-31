# Launch checklist and drafts

Status on 2026-10-31: v0.2.0 Alpha release preparation based on `49ffdb9`.
The release commit and final audited batch are recorded outside the repository
to keep the verified commit clean; see the readiness report. No release tag is
authorized yet. Public PyPI project/version endpoints returned 404, account
access is blocked, and GitHub currently has no `pypi` environment. Codex CLI has a single-call
fixture smoke check; other clients and complete client coverage remain unverified.
The authoritative scope and current evidence are in
[the release readiness report](../audits/release-readiness-2026-10-31.md).

## 1. PyPI (blocking for everything else)

1. Create the project `spring-runtime-mcp` on PyPI (or let the first trusted
   publish create it).
2. On PyPI → project → Publishing, add a trusted publisher:
   - owner: `neilmorse` (current repository owner; the old Kaelenx URL redirects)
   - repository: `spring-runtime-mcp`
   - workflow: `release.yml`
   - environment: `pypi`
3. After a clean-commit gate exits 0, validation-only CI succeeds, account checks
   are complete, and the operator approves publication, tag and push:

   ```bash
   git tag -a v0.2.0 -m "v0.2.0"
   git push origin v0.2.0
   ```

4. The `Release` workflow runs the strict audited gate, validates wheel and sdist
   independently, and publishes those same verified artifacts via OIDC. The updated
   workflow needs a successful remote run. Use `Release validation only` on a
   `codex/release-*` branch first; it has no publish job or OIDC permission.
5. After the package is live, update the README quick start to
   `uvx spring-runtime-mcp --base-url ...` and add the PyPI badge.

## 2. Official MCP Registry

`server.json` declares the 2025-12-11 schema; online Registry validation and account
authorization remain to be checked before submission. The
README contains the ownership token `mcp-name: io.github.Kaelenx/spring-runtime-mcp`,
which the registry checks against the PyPI project description.

After PyPI shows version 0.2.0:

```bash
# install the publisher CLI from the modelcontextprotocol/registry releases
mcp-publisher login github
mcp-publisher publish
```

Verify that the GitHub login authorizes namespace `io.github.Kaelenx`; the
PyPI package must already contain the `mcp-name` token in its README.

## 3. Directory submissions

- **Smithery** — submit the repository at https://smithery.ai/new (or via the
  Smithery CLI once the PyPI package exists). Use the same description as
  `server.json`.
- **awesome-mcp-servers** — open a PR to `punkpeye/awesome-mcp-servers` adding
  under Developer Tools:

  ```markdown
  - [Kaelenx/spring-runtime-mcp](https://github.com/Kaelenx/spring-runtime-mcp) - Read-only, sanitized Spring Boot runtime diagnostics for coding agents: beans and conditions, routes, health, migrations, startup, config origin, OpenAPI and drift.
  ```

- **mcp.so / Glama / PulseMCP** — most index from the official registry, so
  publish there first and only submit manually where a form requires it.

External submissions are visible actions; review the listing text before
sending.

## 4. Launch post draft (r/java, r/springboot, dev.to)

Title: **I built a read-only MCP server that tells your agent why a Spring bean
is missing**

> Coding agents can read a Spring codebase but not what happened at runtime.
> I built `spring-runtime-mcp`, a local stdio MCP server that reads Actuator
> and OpenAPI from an explicitly registered instance and turns it into eight
> bounded, sanitized tools: beans and condition chains, routes, health,
> migrations, startup, config origin, OpenAPI and drift.
>
> It is deliberately narrow: GET only, fixed endpoints, no redirects, no
> heapdump/logfile, no raw env dumps, 16 KiB per response, and missing evidence
> is reported as `partial`/`unknown` instead of a confident guess.
>
> Example from the included Boot 3.4 demo: `springboot_inspect_beans` returns
>
> ```text
> REQUIRED_BEAN_MISSING      (StripeConfiguration#paymentGateway)
>   → SOURCE_FACTORY_NOT_CREATED
>     → PROPERTY_NOT_FOUND   (StripeConfiguration#stripeClient, stripe.enabled)
> ```
>
> Repo: https://github.com/Kaelenx/spring-runtime-mcp (Apache-2.0). Feedback from
> people running Spring Boot 2.7/3.x/4.x in unusual setups is especially
> welcome — synthetic fixtures only go so far.
