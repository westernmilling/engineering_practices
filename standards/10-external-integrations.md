# 10. External Integrations

> Mirrored from Confluence: [10. External Integrations](https://westernmilling.atlassian.net/wiki/spaces/SD/pages/4919689219/10.+External+Integrations)
> Space `SD` · page `4919689219` · last modified in Confluence Oct 27, 2026.
> Confluence is the source of truth; this copy is for reading in-repo and by tooling.

Talking to Agris, Syspro, Great Plains, Microsoft Graph, and anything else we do not own.

---

## Baseline

**None adopted.** Integration guidance in the wild is either vendor-specific or so general as to
be useless. What follows is ours.

Three ideas do the work in §10.1, each answering a different question:

|  | Answers |
| --- | --- |
| **Anti-Corruption Layer** (domain-driven design) | *Put a boundary there* |
| **Single responsibility** — one reason to change | *Why it must be a separate class* |
| **Dependency direction** ([Architecture §1.1](01-architecture.md)) | *Which way the boundary faces* |

A boundary facing the wrong way is just a folder.

---

## 10.1 Clients live in their own layer

**External API integrations live in a dedicated library or infrastructure layer, never in the
service layer.** Clients live in `lib/` (or a shared package in a monorepo) and do not
reference the application ([Architecture §1.1](01-architecture.md)).

- **Each external system gets its own namespace.** `AgrisServices`, `MicrosoftGraph`.
- **A client class handles authentication, HTTP transport and response parsing** — and nothing
else.
- **Business logic that uses a client lives in a service** ([Architecture §1.2](01-architecture.md)).
A client that knows why it is being called has become a service, and now two layers change when
the vendor does.

### Why it has to be a separate class

**A client and a service have different reasons to change** — which is
[single responsibility](https://en.wikipedia.org/wiki/Single-responsibility_principle) in the
formulation that is actually useful here, rather than "does one thing".

|  | Changes when |
| --- | --- |
| **The client** | The vendor changes — an endpoint, an auth scheme, a response shape |
| **The service** | The business changes — a rule, a workflow, what we do with the result |

Vendor systems change on their schedule, not ours, and several of ours are old. Keep them in one
class and a breaking API change is a change to one file, not archaeology across the codebase.

> **The trap in applying this naively.** A client does authentication *and* transport *and*
parsing — three things, so three classes? **No.** All three change for the same reason: the
vendor changed. That is one responsibility at the right granularity, and splitting it buys three
files that always change together. **Count reasons to change, not verbs.**

### Which side defines the shape

The boundary only works if the dependency points the right way — **the client defines the shape,
and the application depends on it.** The client knows nothing about the application
([Architecture §1.1](01-architecture.md)) and translates the vendor's model into types of its own.
Services depend on the client and its types; the vendor's model never reaches them.

In practice that means a client returns **its own** types, not the vendor's. An Agris response
parsed into a `Hash` with the vendor's field names and handed upward has moved the vendor's model
into the service layer, and the boundary is decorative — the class exists but nothing is contained
by it.

**The test:** if Agris renamed a field tomorrow, how many files change? One, the client, means the
vendor's model is contained. More means the client is a pass-through with a namespace.

*The client reaches the service by constructor injection ([Architecture §1.2](01-architecture.md));
the consequence in tests is that doubles are injected rather than patched
([Testing §3.7](03-testing.md)).*

## 10.2 Testing an integration

- **HTTP calls are stubbed, in the Arrange phase** ([Testing §3.7](03-testing.md)).
- **Real network connections are disabled in tests**, except for browser drivers. A suite that can
reach the internet will eventually depend on it, and then it fails for reasons that have nothing
to do with the change.

> **The undocumented-behaviour problem.** Vendor and ERP behaviour is frequently undocumented or
wrong in the documentation, and the only way to learn it is to probe the real system. When you
do, **write down what you found** — a comment at the point it constrains the code
([Coding Style §2.4](02-coding-style.md)), which is exactly the "hidden constraint the code
cannot express" case. A finding that stays in someone's head is one that gets rediscovered the
expensive way.

## 10.3 Error tracking

- **A hosted error tracking service in production.**
- **Background jobs catch, report, then re-raise** so the framework retries
([Architecture §1.5](01-architecture.md)). Catching without re-raising turns a retryable failure
into silent data loss.
- **Configured by environment variable**, never a hardcoded token.
