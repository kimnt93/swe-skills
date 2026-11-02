# Readable TypeScript

- Prettier at 100 columns; one statement per line; no nested ternaries (use early returns or a
  small component).
- A component fits one screen. Split by responsibility: data (a hook), layout, presentational pieces.
- Name components `PascalCase`, hooks `useThing`, event handlers `onThing` (props) / `handleThing` (local).
- Props are a named `interface`; no boolean props that switch behaviour (`<Button primary danger>`):
  use a `variant` union.
- Unions over enums for string sets (`"open" | "filled" | "cancelled"`); exhaustive `switch` with a
  `never` check.
- No `useEffect` to derive state: compute it during render. `useEffect` only to sync with something
  outside React.
- No default exports except where the framework requires them (Next.js pages, layouts, route files).
- Imports: external, then `@/` aliases, then relative; no deep relative chains (`../../../`).
