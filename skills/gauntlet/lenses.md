# Design lenses

Ways of reasoning about a diff, never rules. Use one only when it changes what the author
should do, and say what each way costs. If the code breaks a principle for a good reason, say
that too. Ask these as questions, and name an alternative with its trade-off.

## SOLID

- **Single responsibility.** Count reasons to change, not verbs. Does this class change for more than one reason (a business rule and a display format)? *Trade-off:* splitting gives each reason a home but adds files that must be read together.
- **Open/closed.** Would adding the next variant mean editing this method, or passing in something new? *Trade-off:* extension points cost indirection before a second variant exists.
- **Liskov / interface segregation.** Does a subclass or duck type honour what callers assume? Does a caller depend on methods it never uses? *Trade-off:* narrower interfaces mean more of them.
- **Dependency inversion.** Is the dependency injected (the standards require this) or inverted (the service owns the shape it wants; optional)? *Trade-off:* injection gives testability, and inversion adds insulation from a vendor's types at the cost of an adapter class.

## POODR (Sandi Metz)

- **The wrong abstraction.** Was this extracted from duplication that has shown its shape, or before? *Trade-off:* duplication is cheaper than the wrong abstraction, but three copies of a rule is a bug waiting to diverge.
- **Dependencies and Demeter.** How much does this object know about its collaborators' internals (`a.b.c.d`)? *Trade-off:* a wrapper hides the chain but adds a method per question.
- **Duck types over type checks.** Does a `case` on class stand in for polymorphism? *Trade-off:* polymorphism spreads the logic across classes, and a `case` keeps it in one readable place.

## Tell, don't ask

- Does the caller fetch data from an object and then decide for it? Could the object make that decision? *Trade-off:* behaviour on the object gives one home for the rule, and risks bloating a model with behaviour only one caller needs.

## Clean Code

- **Names.** Does the name reveal intent without the surrounding context? Abbreviations are out (Naming §4.1), and `data` and `tmp` hide what they hold.
- **One level of abstraction per method.** Does one method mix orchestration with detail? *Trade-off:* extracting makes each part short and the whole harder to follow top to bottom.
- **Flag arguments and boolean traps.** Does a boolean argument mean two methods? *Trade-off:* two methods can duplicate the setup.

## Fowler, Patterns of Enterprise Application Architecture

- **Transaction Script vs Domain Model vs Service Layer.** Is the logic where the team expects it? In contracto, services are the Service Layer and `BaseSaveService` and friends are shared Transaction Script. *Trade-off:* scripts are simple until the rules interact, and a richer model costs more up front.
- **Active Record vs Data Mapper.** (ActiveRecord is the default focus; Sequel is Data Mapper-leaning.) Does persistence leak into domain rules, through callbacks or validations that do work? *Trade-off:* Active Record is quick and couples the domain to the table, and a mapper decouples it at the cost of ceremony.
- **Unit of Work.** Which writes must succeed or fail together, and does one transaction cover them? *Trade-off:* a wide transaction holds locks longer, and a narrow one can leave half a record.
- **Query Object / Repository.** Is a complex read tangled into a model or handler? *Trade-off:* a query object names the read and adds a class for a one-off.
- **Gateway.** Does a vendor's type reach a service (Architecture §1.2, External Integrations §10.1)?

## Gang of Four

- **Name the problem first.** Does a pattern here (Strategy, Template Method, Decorator, Adapter, Observer, Factory) name a problem the code actually has? *Trade-off:* a pattern gives a shared vocabulary and adds structure that must earn its keep.
- Prefer composition to inheritance: does a subclass exist only to share code? *Trade-off:* composition needs wiring, and inheritance couples the child to the parent.

## Domain-Driven Design

- **Aggregates and consistency boundaries.** What must be consistent immediately (inside one transaction) and what can be eventually? A parent saved without its children is a boundary question. *Trade-off:* a big aggregate is simple to keep consistent and slow to load and lock, and a small one scales and needs compensating steps.
- **Value objects.** Is a primitive (an amount, a date range, a status string) carrying rules that belong on a type? *Trade-off:* a type enforces the rule once, and adds a class to convert at the edges.
- **Ubiquitous language and bounded contexts.** Does the code use the business's word for this? Does the same word mean two things (`item`, `contract`)? *Trade-off:* renaming to match the domain costs churn now and saves translation later.
- **Anti-corruption layer.** Where an external system's model meets ours, is there a seam?
