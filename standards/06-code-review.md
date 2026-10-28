# 6. Code Review

> Mirrored from Confluence: [6. Code Review](https://westernmilling.atlassian.net/wiki/spaces/SD/pages/4918738946/6.+Code+Review)
> Space `SD` · page `4918738946` · last modified in Confluence Oct 27, 2026.
> Confluence is the source of truth; this copy is for reading in-repo and by tooling.

How review feedback is delivered. **Not** who owns the code, and not when it merges.

---

## Baseline

**[Google's engineering practices — code review](https://google.github.io/eng-practices/review/)**,
both halves: the reviewer's guide and the author's guide.

What we take from it, and do not restate here:

- **The standard of review** — approve when the change definitely improves overall code health,
even if it is not perfect. Perfection is not the bar; improvement is.
- **What a reviewer looks at** — design, functionality, complexity, tests, naming, comments,
style, documentation.
- **Review speed** — a slow review costs more than most of what it catches.
- **How to write a comment** — explain the *why*, balance a directive with a reason, be kind
about the person and precise about the code.

*Unversioned, but actively maintained and stable. If it changes materially, this page is where
the deltas would land.*

---

## 6.1 The lifecycle

```
Local development
      │
      ▼
Draft PR                    early, evolving work
      │                     directional feedback · design validation · risk
      ▼
Mark ready for review       Draft → Open
      │                     full human review begins
      ▼
Open PR                     ready for approval
      │                     changes addressed · sign-off recorded
      ▼
Merge                       squash, by a human
```

The states exist to calibrate review effort to the state of the work. A comment that would be
right on an open PR is often wasted on a draft.

## 6.2 PR-first

**All initial feedback happens in the pull request.** Written, specific, actionable.

Questions, concerns and suggestions belong in PR comments so that context, decisions and
learning are preserved. This is not bureaucracy — it is what makes the review a durable record
rather than a conversation two people remember differently.

## 6.3 Draft PRs

Use a draft when code is pushed but not ready for final review.

Early review on drafts is **encouraged**, especially for directional feedback, design
validation, and risk or complexity assessment. But a draft is a **moving target** and may change
substantially — so feedback on one should aim at guidance and alignment, not polish or
completeness.

## 6.4 Ready for review

Moving Draft → Open signals three things:

1. The author believes the change is ready for full review.
2. Requirements and intent are understood and implemented.
3. The PR is ready for detailed feedback and approval.

> **⚠ Open decision — automated pre-review.** The superseded Code Review Communication Standard
required **Copilot review on every open PR**, to catch common issues early and reduce reviewer
load. Nothing else in the corpus mentions Copilot, and a reviewer agent is treated everywhere
else as a convenience rather than a substitute. These positions contradict.
> 
> Three ways to settle it: require an automated pre-review and name the tool · make it explicitly
optional and delete the requirement · defer until an adversarial-review design lands, since
that may replace it entirely.
> 
> **This section is not final until that is decided.**

## 6.5 Moving to a live conversation

Live discussion is encouraged **after written feedback exists**, when it will reduce excessive
back-and-forth, clarify a nuanced design decision, or unblock progress faster.

Live conversation is a tool for **resolution, not first contact**.

**Outcomes and decisions from that conversation are summarised back in the PR.** A decision made
on a call and not written down did not happen, as far as anyone reading the history later is
concerned.

## 6.6 When a PR misses the requirement

Sometimes a PR fundamentally misses the original intent. Then:

- Say so clearly **in the PR**.
- A live conversation is usually the fastest way to realign.
- Summarise the outcome back in the PR, or in a linked document.

## 6.7 Expectations

**Reviewers**

- Be constructive, respectful, and clear about *why* a change is requested.
- No drive-by or vague comments.
- Be available to support your feedback, including joining a call when that is what it takes.

**Authors**

- Treat written feedback as collaborative, not personal.
- Ask clarifying questions in the PR when a comment is unclear.
- Propose a live discussion yourself if written comments become inefficient.

---

## What this page does not cover

- Attributable sign-off before merge, and who owns the outcome.
- Correcting in the PR rather than locally.
- The human reads every line.
- Tagging corrections with their cause.

**PR size, and pushing back on one too large to review**, is
[Version Control §5.5](05-version-control.md).

## Considered and not adopted

**[Conventional Comments](https://conventionalcomments.org/)** — a labelling convention for
review comments (`praise:`, `nitpick:`, `issue:`, `suggestion:`, with `(blocking)` /
`(non-blocking)` decorations).

Not adopted, for three reasons:

1. **It is unversioned**, so it can change under us without notice.
2. **It collides with correction-cause tagging**, which already claims the first word of a review
comment. You cannot write `issue: context: …`.
3. **It solves a problem of scale we do not have.** The labels earn their keep when many
reviewers produce ambiguous tone at volume. At four engineers, "be clear about why" does the
same work.

If it is ever wanted, the clean merge is to make correction causes **decorations** rather than
prefixes — `issue (context):` — which the convention explicitly supports for
organisation-specific tags. That would cost one more convention to remember, on a practice
already judged borderline.

---

> **Write first, talk second, document always.**
