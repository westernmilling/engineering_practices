# Front-end lenses

For diffs that touch React components, hooks and other browser code in JavaScript or TypeScript. Like
`lenses.md`, these are ways of reasoning about a diff, never rules. Use one only when it changes what
the author should do, and say what each way costs. Ask as questions, and name an alternative with its
trade-off. If the code breaks a guideline for a good reason, say that too.

Server-side TypeScript uses the design lenses in `lenses.md` and the **Types** section here. The React
sections do not apply to it.

## Correctness in the browser

Look here first, as in any review. The front-end versions of "what if the second write fails":

- **Races and stale responses.** Can a slower, earlier request land after a newer one and overwrite it (typing in a search box, changing a route, unmounting mid-request)? *Trade-off:* ignoring stale results (an abort signal, or a flag in the effect cleanup) is a few lines per fetch, and a data-fetching library handles it once and adds a dependency.
- **Double submit and retries.** What happens if the user clicks twice, or the request is retried? *Trade-off:* disabling the button is cheap and only covers the UI; an idempotency key on the server is stronger and needs the server to take part.
- **Optimistic updates.** If the request fails, does the screen roll back and tell the user? *Trade-off:* optimistic updates feel instant and need rollback and reconcile code; waiting for the server is simpler and feels slower.
- **Loading, empty and error states.** What does the user see while it loads, with no data, and when it fails? *Trade-off:* each state is more UI to build and test, and a skipped one shows up as a blank screen or a spinner that never ends.
- **Everything shipped to the browser is public.** Is a token, key or internal URL in the bundle or in client-side config? *Trade-off:* routing the call through the server keeps the secret and adds a hop.

## State and effects

- **Where should this state live?** In the component, lifted to a parent, in the URL, in a server-data cache, or global? *Trade-off:* local state is simplest and gets duplicated when two places need it; lifting or sharing it removes the duplication and couples the components that read it.
- **Derived state.** Is something stored in state that could be computed from props or other state? *Trade-off:* computing it on render cannot drift out of date; storing it saves the work and needs code to keep it in sync.
- **Effects.** Is this effect syncing with something outside React (a subscription, the DOM, a request), or is it reacting to something the event handler could do directly? Is the dependency list honest, or is the lint rule switched off? *Trade-off:* doing the work in the handler is simpler and easier to follow; an effect is right for outside systems, and a suppressed dependency hides stale values.
- **Parse once, at the edge.** Do dates, numbers and ids arrive as strings and get parsed in several places? *Trade-off:* parsing in one place makes the inside trustworthy, at the cost of a conversion layer and a place that must know every field's shape.

## Components and composition

- **One component, one reason to change.** Does this component fetch, decide and lay out? *Trade-off:* a custom hook or a container and presentational split gives each reason a home, and adds files that must be read together.
- **Props that smell.** A boolean prop that switches the layout (a boolean trap), a long list of props, or a value passed down through several levels. *Trade-off:* composition (children, slots) or context removes the drilling, and context hides where the data comes from.
- **Names, from the reader's seat.** Does the name say what it is without the surrounding code (`contractFormOpen` and not `open`, `errorMessage` for a string and `hasError` for a boolean, a form and a form in a modal)? *Trade-off:* longer names cost width and save the reader a trip to the definition.
- **Memoisation.** Is `useMemo`, `useCallback` or `memo` added without a measured need? *Trade-off:* it can stop re-renders, adds dependency lists to keep right, and can hide the real cause of a slow render.

## Types (TypeScript)

- **`any` and casts at a boundary.** Is `any` or `as` standing in for a real type, especially for data from the network? *Trade-off:* validating at the edge with a schema makes everything behind it trustworthy and adds code and a dependency; a cast is quick and fails at runtime.
- **Variants.** Are the cases of one thing modelled as optional fields, or as a tagged union with a literal `type`? *Trade-off:* a union makes every case handled, and costs some type ceremony. Enums or `as const` avoid casts when a string `type` is widened.
- **Hand-written or generated types.** Does a type copy a shape the backend already defines? *Trade-off:* generated types follow the source and need tooling to be worth it; hand-written ones are quick and drift.

## Accessibility and the user

- **Can it be used without a mouse?** Is it a real `button` or link, or a clickable `div`? Does every input have a label, and is focus managed when something opens or closes? *Trade-off:* native elements are free; a custom widget needs the keyboard and ARIA work rebuilt by hand.
- **Is meaning carried by colour alone?** Is there also text, an icon or a pattern? *Trade-off:* the extra cue is a little more design and covers people who cannot see the difference.

## Performance

- **Render cost and size.** Is expensive work done on every render, a long list rendered whole, or a heavy library imported for one function? *Trade-off:* virtualising, lazy loading or a lighter import cost complexity, so measure before the change and say so.
- **Many rows.** How does this behave with 10,000 of them? *Trade-off:* paging or windowing keeps it fast and changes how the user scrolls and searches.

## Testing front-end code

Use this section for JavaScript and TypeScript tests, not the Ruby and RSpec guidance in `digest.md`. The principles carry over (test what is observable, say what a test is for). The RSpec mechanics, such as `let`, `subject` and Arrange blocks, do not.

- **Behaviour, not internals.** Does the test assert what the user sees and does, or component state, calls to a hook, or a snapshot of a large tree? *Trade-off:* behaviour tests survive refactors and take more setup; internals tests are quick and break on every refactor.
- **How elements are found.** By role, label and text, by test id, or by CSS and DOM structure? *Trade-off:* role and label queries also check accessibility; test ids stay stable and say nothing about what the user can find.
- **Names, from the user's seat.** Does the name say what the user does and sees ("when the user creates an organisation they see it in the table")? *Trade-off:* a longer name reads as a sentence and costs width.
- **Mocks.** Is the network mocked at its edge, or is a hook or module replaced? *Trade-off:* mocking the network exercises more of the real code; replacing a module is simpler and tests less.
- **Waiting.** Does it wait a fixed time, or wait for the thing the user would wait for? *Trade-off:* waiting for the result is steadier and needs a clear signal in the UI.
- **Does it earn its place?** Is it testing our code, or the router, the form library or a date helper? *Trade-off:* a test of the library adds confidence about an upgrade and costs a test to maintain.
