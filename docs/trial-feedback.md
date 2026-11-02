# First-query trial and feedback

[First query](first-query.md) · [Chinese overview](../README.zh-CN.md) · [Synthetic route demo](demo.md)

Try one question that you can check independently: whether a known route is registered, and which Controller handles it. Use an application you own or are authorized to inspect. The synthetic demo is also useful when you have no application ready; label the report as synthetic replay.

## What makes a useful report

Use the [first-query feedback template](../.github/ISSUE_TEMPLATE/first-query-feedback.md) and paste it into a [new GitHub issue](https://github.com/neilmorse/spring-runtime-mcp/issues/new). Record the date, package/client/OS versions, evidence type, expected observation, actual result, and the stage that passed or failed. A first attempt is useful even if you could not complete a query.

| Stage | Evidence to record |
| --- | --- |
| Installation and registration | Package version and whether the client loaded the server configuration. |
| MCP initialization and discovery | Whether initialization succeeded and eight tools were discovered; not applicable for offline replay. |
| Authorized target access | Whether the required fixed endpoint was readable; not applicable for offline replay. |
| Independently checked query | The tool/arguments, selected result fields, and how the result was checked against an approved source or observation. |

For each stage use `passed`, `failed`, `not attempted`, `unknown`, or `not applicable`. Registration does not prove a tool call, and a tool call does not by itself prove that its output matches the application.

A public report should contain only reviewed, minimal information: versions, fixed diagnostic/gap codes, a redacted route selector, counts and coverage, and a short description of the comparison. Remove identifying service names, hostnames, source paths, or screenshots as needed. Keep credentials, raw Actuator bodies, env/configprops value trees, logs, and stack traces out of issues. Use the [security reporting policy](../SECURITY.md) for vulnerabilities.

Choose whether the maintainer may cite your report or handle in public case studies. Citation permission defaults to no. A report being public does not by itself authorize a testimonial or an endorsement.

## Short invitation to share yourself

```text
I maintain spring-runtime-mcp, an early-stage Apache-2.0 MCP server for read-only Spring Boot runtime diagnostics. I am looking for developers to try one route query and report where setup succeeds or gets stuck. There is also a synthetic demo that needs no running Spring application.

English guide: https://github.com/neilmorse/spring-runtime-mcp/blob/master/docs/first-query.md
Synthetic demo: https://github.com/neilmorse/spring-runtime-mcp/blob/master/docs/demo.md
Feedback template: https://github.com/neilmorse/spring-runtime-mcp/blob/master/.github/ISSUE_TEMPLATE/first-query-feedback.md
```
