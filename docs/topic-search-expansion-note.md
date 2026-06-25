# Topic Search Expansion Note

This note records the current decision on topic expansion for evidence-pack searches.

## Current Behaviour

`assurance report evidence-pack` passes the topic text through to the selected evidence sources:

- Confluence uses CQL `text ~ "<topic>"`.
- Jira uses JQL `text ~ "<topic>"`.
- Azure Resource Graph searches resource names with `contains`.
- Local code search currently uses a case-insensitive substring search over candidate files, plus `git log --grep` for commits.

Confluence and Jira already apply their own search tokenisation and matching behaviour. For example, a manual Confluence search for `payment` can return pages containing `payments`. We should rely on that native behaviour unless we have evidence that important results are being missed.

## Decision

Do not implement topic expansion by default at this stage.

Topic expansion could make searches broader, but it also introduces noise and can become hard to explain. Assurance evidence needs to remain traceable: reviewers should understand why a result was included.

## Why Not Yet

Naive expansion is risky:

- `reject` can sensibly expand to `rejects`, `rejected`, `rejecting`, `rejection`.
- `payment` should usually expand only to `payment`, `payments`.
- Blind suffix rules would create bad terms such as `paymented`.

Lemmatization or stemming libraries could help, but they add dependency weight and still require source-specific query construction. They may also behave differently from Confluence, Jira, Azure, and local code search.

## When To Revisit

Reconsider topic expansion if we see real missed evidence, especially in:

- Local code searches where phrase variants differ, such as `reject payment` versus `reject payments`.
- Jira or Confluence searches where native matching does not find expected singular/plural or verb-form variants.
- Domain-specific terminology where aliases matter, such as `payment`, `transaction`, `authorisation`, `auth`.

If implemented later, prefer an opt-in flag rather than changing defaults:

```bash
assurance report evidence-pack "reject payment" --expand-topic
```

The evidence pack should then include a visible search strategy section listing the original topic, generated terms, and generated phrase variants.

