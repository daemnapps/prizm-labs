# <Brand> — web design tokens

Read off the brand's own live CSS (<which files, which site>) on <date>.
**Measured, not chosen** — same rule as `palette.md`. `palette.md` is sampled from
product photography; this file from the web surfaces. Keep them apart.

## Colour

| Token | Hex | What it is | Where it earns its place |
|---|---|---|---|
| open | `#000000` | <the ground, the page, the accent…> | <selectors and count, from the CSS> |

## Roles — what each colour is FOR

| Token | Role |
|---|---|
| open | the ground |
| open | the page |
| open | the action |
| open | value only — never decoration |

## Type

| Role | Family | Weights | Fallback |
|---|---|---|---|
| Display | open | | |
| Body | open | | |

## Shape

| Token | Value | Where |
|---|---|---|
| radius | open | |
| button | open | |

## As CSS custom properties

```css
:root {
  --brand--color--ground: #000000;   /* open */
  --brand--color--page:   #FFFFFF;   /* open */
  --brand--color--accent: #000000;   /* open */
  --brand--font--display: "open", serif;
  --brand--font--body:    "open", sans-serif;
}
```
