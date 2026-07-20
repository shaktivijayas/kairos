---
name: KAIROS
description: Ambient compliance shield for India's micro-merchants — calm, precise, no ERP required.
colors:
  warm-neutral-bg: "oklch(96.1% .011 92)"
  warm-neutral-surface: "oklch(95.5% .006 90)"
  near-black-ink: "oklch(18% 0 0)"
  ink-on-primary: "oklch(100% 0 0)"
  muted-ink: "oklch(45% .008 90)"
  border-neutral: "oklch(88% .005 90)"
  alert-red: "oklch(57.7% .245 27.325)"
  alert-red-ink: "oklch(98.4% .003 247.858)"
  verified-green: "oklch(59.6% .145 163.225)"
  verified-green-ink: "oklch(43.2% .095 166.913)"
  signal-lime: "#d7ff3f"
  signal-lime-ink: "#5a7a00"
typography:
  display:
    fontFamily: "Space Grotesk, ui-sans-serif, system-ui, sans-serif"
    fontSize: "clamp(2.25rem, 5vw, 3.75rem)"
    fontWeight: 700
    lineHeight: 1
    letterSpacing: "-0.025em"
  headline:
    fontFamily: "Space Grotesk, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.875rem"
    fontWeight: 500
    lineHeight: 1.2
  title:
    fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 600
    lineHeight: 1.4
  body:
    fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 500
    lineHeight: 1.25
rounded:
  sm: "6px"
  md: "8px"
  lg: "10px"
  xl: "14px"
  2xl: "18px"
  3xl: "22px"
  full: "9999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "40px"
  2xl: "56px"
  3xl: "64px"
components:
  button-primary:
    backgroundColor: "{colors.near-black-ink}"
    textColor: "{colors.ink-on-primary}"
    rounded: "{rounded.lg}"
    padding: "8px 16px"
  button-primary-hover:
    backgroundColor: "{colors.near-black-ink}"
    textColor: "{colors.ink-on-primary}"
  button-secondary:
    backgroundColor: "{colors.warm-neutral-surface}"
    textColor: "{colors.near-black-ink}"
    rounded: "{rounded.lg}"
    padding: "8px 16px"
  badge-flag-red:
    backgroundColor: "{colors.alert-red}"
    textColor: "{colors.alert-red-ink}"
    rounded: "{rounded.full}"
  badge-flag-green:
    backgroundColor: "{colors.verified-green}"
    textColor: "{colors.verified-green-ink}"
    rounded: "{rounded.full}"
  badge-flag-lime:
    backgroundColor: "{colors.signal-lime}"
    textColor: "{colors.near-black-ink}"
    rounded: "{rounded.full}"
  card:
    backgroundColor: "{colors.warm-neutral-surface}"
    textColor: "{colors.near-black-ink}"
    rounded: "{rounded.xl}"
    padding: "24px"
---

# Design System: KAIROS

## 1. Overview

**Creative North Star: "The Quiet Ledger"**

KAIROS reads like a ledger that has learned to speak: a calm, warm-neutral surface that never competes for attention, near-black ink for anything that needs to be read carefully, and exactly one loud color — a chartreuse-lime signal — reserved for the moment something actually needs the user's eyes. The system is built on shadcn/ui primitives (visible in the token names: `card`, `popover`, `sidebar`, `ring`) run through Tailwind v4's OKLCH pipeline, paired with Space Grotesk for display type and Inter for everything else. Nothing here is decorative; the restraint is the point — a compliance tool for someone running a business alone has to be trusted at a glance, not admired.

This system explicitly rejects the generic navy-and-chart-heavy enterprise fintech look (per PRODUCT.md's anti-references) and the dense, bureaucratic feel of a government tax portal. Warmth comes from the near-white neutral base, not from saturation; authority comes from precision and restraint, not from weight or scale.

**Key Characteristics:**
- One warm-neutral field, one near-black ink, one loud accent — never more than one saturated color live on screen at once
- Flat at rest; elevation only appears in response to interaction
- Display type (Space Grotesk) is reserved for headings; body copy stays in Inter, small and legible
- Severity is color-coded but never alarmist — red, lime, and green each carry a matched "ink" pairing for contrast, not just a raw hue

## 2. Colors

The palette is deliberately narrow: a warm-neutral field and near-black ink carry almost everything, with three signal colors reserved strictly for compliance severity (red / lime / green).

### Primary
- **Near-Black Ink** (oklch(18% 0 0)): The `primary` token — used for primary buttons, headings, and body text. Carries near all of the interface's visual weight.

### Secondary
- **Signal Lime** (#d7ff3f): A loud chartreuse-lime accent, paired with **Near-Black Ink** (oklch(18% 0 0)) for on-accent text — *not* the separate Signal Lime Ink swatch below. Reserved for a single flagged/highlighted state — this is the one color allowed to break the calm.
- **Signal Lime Ink** (#5a7a00): computed at ≈4.33:1 on Signal Lime, this token fails the 4.5:1 threshold at label/badge text sizes (≤14px, non-bold). Keep it defined for large/bold display use only (≥18px, or ≥14px bold); default to Near-Black Ink for anything smaller, which measures ≈12.2:1 on the same background. (Corrected during `/impeccable critique` — the original spec paired label-sized text with this token.)

### Tertiary
- **Verified Green** (oklch(59.6% .145 163.225), Tailwind emerald-600) with **Verified Green Ink** (oklch(43.2% .095 166.913), emerald-800): the positive/deduction-opportunity signal — a finding worth claiming, not worth worrying about.
- **Alert Red** (oklch(57.7% .245 27.325)) with **Alert Red Ink** (oklch(98.4% .003 247.858)): the cash-limit-breach / high-risk signal.

### Neutral
- **Warm Neutral Grey (Background)** (oklch(96.1% .011 92)): the base surface — a soft, warm off-white, not stark white.
- **Warm Neutral Grey (Surface)** (oklch(95.5% .006 90)): cards, popovers, secondary buttons, muted fills — very slightly cooler and flatter than the page background so raised surfaces read as distinct without a shadow.
- **Muted Ink** (oklch(45% .008 90)): secondary/muted text — captions, timestamps, helper copy.
- **Border Neutral** (oklch(88% .005 90)): all borders and input strokes; low-contrast by design, since the system leans on fills over lines to separate content.

### Named Rules
**The One Signal Rule.** Signal Lime, Alert Red, and Verified Green each appear alone, never combined on the same element or stacked in the same view without reason — every saturated color on screen is there to mean something specific (a severity), never for decoration.

## 3. Typography

**Display Font:** Space Grotesk (weights 500, 700), with `ui-sans-serif, system-ui, sans-serif` fallback
**Body Font:** Inter (weights 400, 500, 600), with `ui-sans-serif, system-ui, sans-serif` fallback

**Character:** A geometric, slightly technical display face over a warm, highly legible body face — precise without being cold. The pairing gives headings a bit of engineered confidence while keeping every sentence a user actually has to read (findings, reasoning, disclaimers) plain and easy.

### Hierarchy
- **Display** (700, `clamp(2.25rem, 5vw, 3.75rem)`, line-height 1): hero/landing headline only.
- **Headline** (500, 1.875rem, line-height 1.2): section headings, page titles.
- **Title** (600, 1.25rem, line-height 1.4): card titles, dialog titles, finding headers.
- **Body** (400, 1rem, line-height 1.5): all reading content — findings, reasoning, chat answers. Cap at 65–75ch per line.
- **Label** (500, 0.875rem, line-height 1.25): buttons, form labels, badges, timestamps.

### Named Rules
**The Plain-Language Rule.** Body and label text default to Inter at regular/medium weight — no jargon-signaling italics, no small-caps. Given the audience (mobile-first, not fluent in tax terminology), clarity always wins over typographic flourish.

## 4. Elevation

Flat-by-default. Surfaces sit at the same visual plane as the warm-neutral background at rest, separated only by the subtle shift from `warm-neutral-bg` to the slightly flatter `warm-neutral-surface` fill — not by shadow. Shadow is reserved for state: a hover lift on interactive cards, a popover or dialog breaking out of the page plane, or a focus ring on inputs. The stylesheet carries Tailwind's default shadow scale (xs through xl); this project uses it sparingly rather than by default.

### Shadow Vocabulary
- **shadow-xs** (`0 1px 2px 0 rgba(0,0,0,.05)`): barest separation — inputs on focus, subtle card edges.
- **shadow-sm** (`0 1px 3px rgba(0,0,0,.1), 0 1px 2px -1px rgba(0,0,0,.1)`): default raised-card state, if a card needs to lift at all.
- **shadow-md / shadow-lg / shadow-xl**: reserved for overlays — popovers, dialogs, dropdowns — never for static page content.

### Named Rules
**The Flat-Until-Floating Rule.** Anything anchored to the page (cards, sections, the dashboard ledger) stays flat. Shadow only appears on anything that floats above the page plane (popovers, dialogs, dropdowns) or responds to direct interaction (hover, focus).

## 5. Components

Crisp and official: components favor sharp, exact edges and firm color assignment over softness or decoration. Nothing is styled to be liked — it's styled to be trusted, in keeping with a statutory-compliance tool.

### Buttons
- **Shape:** `rounded-lg` (10px) — a shadcn-default corner radius, not sharp, not pill-shaped.
- **Primary:** Near-Black Ink background, white (`ink-on-primary`) text, `px-4 py-2` (16px/8px) padding.
- **Secondary / Ghost:** Warm-Neutral Surface background with Near-Black Ink text; ghost variant drops the fill entirely and relies on the same ink color plus a hover-state surface fill.
- **Hover / Focus:** subtle background-color shift within the same token family (no color changes on hover, only tone); focus uses the `ring` token as an outline, never a color swap.

### Badges (severity)
- **Style:** `rounded-full` pill, `signal-lime` / `alert-red` / `verified-green` background paired with a contrast-checked ink for text — never a raw white-on-saturated pairing. Alert Red and Verified Green pair with their own dedicated ink tokens; Signal Lime pairs with **Near-Black Ink**, not its own ink swatch (see Colors correction above).
- **Use:** one badge per finding, color mapped directly to severity (red = cash-limit breach, lime = flagged/needs review, green = deduction opportunity).

### Cards / Containers
- **Corner Style:** `rounded-xl` (14px) — one step softer than buttons, so containers read as distinct from interactive controls.
- **Background:** Warm-Neutral Surface.
- **Shadow Strategy:** flat at rest (see Elevation); a card only lifts on hover if it's directly actionable (e.g., a clickable finding).
- **Border:** Border Neutral, 1px, low-contrast — a quiet separator, not a strong outline.
- **Internal Padding:** 24px (`{spacing.lg}`).

### Inputs / Fields
- **Style:** Border Neutral stroke, Warm-Neutral Surface or transparent background, `rounded-lg` (10px).
- **Focus:** ring token outline (`--ring`), no border-color change — keeps the calm palette intact even in an active state.
- **Error:** switches the ring/border to Alert Red; error copy stays in Body typography, not a smaller or louder size — errors are informative, not shouted.

### Navigation
Not independently confirmed from the rendered app (this DESIGN.md was extracted from the production stylesheet and the shadcn/ui token set it's built on, not from a fully rendered page — the SPA's routed content wasn't inspectable via static fetch). Treat nav styling as inherited from the same token system (Warm-Neutral Surface fill, Near-Black Ink text/icons, Signal Lime reserved for an active/alert indicator only) until confirmed on a re-run of `/impeccable document` against the rendered app.

## 6. Do's and Don'ts

### Do:
- **Do** keep the interface to one warm-neutral field, one near-black ink, and exactly one live saturated color per screen — Signal Lime, Alert Red, or Verified Green, chosen by what's actually being flagged.
- **Do** pair every saturated accent with a contrast-checked ink for on-accent text: `alert-red` → `alert-red-ink`, `verified-green` → `verified-green-ink`, `signal-lime` → `near-black-ink` (not `signal-lime-ink`, which only clears 4.5:1 at large/bold sizes); never default to plain white on a saturated fill.
- **Don't** use Signal Lime as a purely decorative accent (a status dot, a hover flourish) with no severity meaning attached — it means "flagged," full stop.
- **Do** keep cards and page sections flat at rest; reserve shadow for anything that floats (popovers, dialogs, dropdowns) or is mid-interaction (hover, focus).
- **Do** default to Inter at regular/medium weight for anything the user has to actually read — findings, reasoning, disclaimers, chat answers.
- **Do** frame every AI-generated finding or answer as worth reviewing with a CA, never as confident tax advice — visual weight (badge severity, headline size) should track the same restraint as the copy.

### Don't:
- **Don't** build a generic navy-and-chart-heavy enterprise fintech dashboard — this tool serves one solo user, not a finance team (see PRODUCT.md anti-references).
- **Don't** replicate a government/tax-portal UI: no dense multi-column forms, no bureaucratic all-caps labels, no GSTN-portal-style density.
- **Don't** use `border-left`/`border-right` colored stripes as a severity indicator — severity is a badge (rounded-full, filled, matched ink), never a side stripe.
- **Don't** apply Signal Lime decoratively (as a hover accent, a link color, a random highlight) — it means "flagged," and diluting that meaning undercuts the one thing the accent is for.
- **Don't** add shadow to static, at-rest page content — shadow is reserved for floating/interactive elements only.
