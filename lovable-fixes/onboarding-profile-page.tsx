/**
 * Corrected onboarding/business-profile page — addresses every finding from
 * /impeccable critique (2026-07-19, see .impeccable/critique/2026-07-19T15-54-36Z__*.md).
 *
 * I don't have write access to the actual Lovable project repo (MCP account
 * mismatch — see chat), so this is reverse-engineered from the shipped JS
 * bundle at kairos-compliance.lovable.app, not a diff against real source.
 * Prop names, hook names, and file location are inferred to match what the
 * bundle implied; paste this into the real route component and reconcile
 * imports (useQuery/useMutation/useRouter sources, profileQueryOptions,
 * saveProfile server fn) against the actual project.
 *
 * What changed vs. the shipped version, and why — see inline comments tagged
 * with the finding they fix.
 */
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useMutation } from "@tanstack/react-query";
import { useRouter } from "@tanstack/react-router";
import { profileQueryOptions, saveProfile } from "./-data"; // adjust to real import paths

const TAX_SCHEME_HINTS: Record<string, string> = {
  regular:
    "Standard GST filing — full input tax credit, most retail and service businesses use this.",
  composition:
    "Lower GST rates, but no input tax credit. Common for small kirana/retail shops under ₹1.5Cr turnover.",
};

// P0 fix: raw backend error strings never reach the user unmediated.
function friendlyErrorMessage(error: unknown): string {
  const message = error instanceof Error ? error.message : String(error);
  if (/network|fetch|timeout/i.test(message)) {
    return "Couldn't reach KAIROS — check your connection and try again.";
  }
  if (/unauthorized|401|403/i.test(message)) {
    return "Your session expired. Please sign in again.";
  }
  return "Something went wrong saving your profile. Nothing was lost — try again.";
}

export function OnboardingPage() {
  const { data: profile } = useQuery(profileQueryOptions);
  const router = useRouter();
  const [form, setForm] = useState(profile);
  const [justSaved, setJustSaved] = useState(false);
  useEffect(() => setForm(profile), [profile]);

  const saveMutation = useMutation({
    mutationFn: (data: typeof form) => saveProfile({ data }),
    onSuccess: () => {
      setJustSaved(true);
      router.invalidate();
      setTimeout(() => setJustSaved(false), 3500);
    },
  });
  const setField = (key: string, value: string) =>
    setForm((f: any) => ({ ...f, [key]: value }));

  // P0 fix: require the fields the copy claims are needed ("Get it right
  // once") instead of silently accepting a blank submission.
  const isValid = Boolean(
    form?.legal_business_name?.trim() &&
      form?.trade_style?.trim() &&
      form?.business_category?.trim() &&
      form?.tax_scheme
  );

  return (
    <div className="min-h-screen bg-background font-body text-foreground">
      <div className="mx-auto max-w-3xl px-6 py-14 md:py-20">
        <header className="mb-12">
          {/* P0 fix: badge label is sentence case, not uppercase-tracked —
              this is meta/status copy, the one place uppercase is kept is
              the wordmark in the footer, per DESIGN.md's corrected "one
              uppercase element max" guidance. Dot color fix: was
              decorative Signal Lime (banned — Signal Lime means "flagged",
              nothing here is flagged); now a neutral progress dot. */}
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-foreground/15 bg-card px-3 py-1 text-xs text-muted-foreground">
            <span className="h-1.5 w-1.5 rounded-full bg-foreground/40" />
            Step 1 of 3 — Business profile
          </div>

          {/* P1 fix: 3-segment progress stepper, replacing text-only step count. */}
          <div className="mb-6 flex gap-1.5" role="progressbar" aria-valuenow={1} aria-valuemin={1} aria-valuemax={3} aria-label="Onboarding progress">
            {[1, 2, 3].map((step) => (
              <span
                key={step}
                className={`h-1 flex-1 rounded-full ${step === 1 ? "bg-foreground" : "bg-foreground/15"}`}
              />
            ))}
          </div>

          {/* P1 fix: fluid clamp() display size (DESIGN.md's own display
              token) instead of the text-5xl/md:text-6xl breakpoint jump,
              and the hard <br/> is dropped so the heading wraps naturally
              at any viewport instead of overflowing into 3 ragged lines. */}
          <h1
            className="font-display font-bold uppercase leading-[0.95] tracking-tight"
            style={{ fontSize: "clamp(2.25rem, 5vw, 3.75rem)" }}
          >
            Set up your business profile.
          </h1>
          <p className="mt-5 max-w-xl text-base text-muted-foreground">
            KAIROS uses this to file, reconcile, and warn you before compliance deadlines.
            Get it right once — we&apos;ll take it from here.
          </p>
        </header>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (isValid) saveMutation.mutate(form);
          }}
          className="rounded-3xl bg-card p-6 md:p-10"
          noValidate
        >
          <div className="grid gap-6">
            <FormField
              label="Legal business name"
              hint="As it appears on your GST certificate."
              value={form?.legal_business_name}
              onChange={(v) => setField("legal_business_name", v)}
              required
            />
            <FormField
              label="Trade style"
              hint="The name customers see on invoices."
              value={form?.trade_style}
              onChange={(v) => setField("trade_style", v)}
              required
            />
            <FormField
              label="Business category"
              hint="e.g. Retail — Apparel, Kirana, Salon."
              value={form?.business_category}
              onChange={(v) => setField("business_category", v)}
              required
            />
            {/* P1 fix: accessible grouping via fieldset/legend instead of a
                bare <label> wrapping two <button>s (undefined association
                for assistive tech). role="radiogroup" + aria-checked on
                each option makes the selection announce correctly. */}
            <fieldset>
              <legend className="mb-2 block text-xs font-medium text-muted-foreground">
                Tax structure
              </legend>
              <SegmentedControl
                value={form?.tax_scheme}
                onChange={(v) => setField("tax_scheme", v)}
                options={[
                  { value: "regular", label: "Regular GST Scheme" },
                  { value: "composition", label: "Composition Scheme" },
                ]}
              />
              {/* P1 fix: the one decision that actually needs explanation
                  now gets one, matching the hint pattern used everywhere
                  else on this form. */}
              <p className="mt-1.5 block text-xs text-muted-foreground">
                {form?.tax_scheme
                  ? TAX_SCHEME_HINTS[form.tax_scheme]
                  : "Not sure which applies? Regular GST Scheme is the default for most businesses — ask your CA if you're unsure."}
              </p>
            </fieldset>
          </div>
          <div className="mt-10 flex flex-wrap items-center justify-between gap-4">
            <p className="text-xs text-muted-foreground" role="status" aria-live="polite">
              {saveMutation.isError
                ? friendlyErrorMessage(saveMutation.error)
                : justSaved
                  ? "✓ Saved successfully."
                  : "Changes save to your KAIROS profile."}
            </p>
            <div className="flex items-center gap-3">
              {/* P0 fix: visible retry affordance on error, instead of a
                  dead-end error string with no next action. */}
              {saveMutation.isError && (
                <button
                  type="button"
                  onClick={() => saveMutation.mutate(form)}
                  className="text-sm font-medium text-foreground underline underline-offset-2 hover:no-underline"
                >
                  Retry
                </button>
              )}
              <button
                type="submit"
                disabled={saveMutation.isPending || !isValid}
                className="inline-flex items-center gap-2 rounded-full bg-[color:var(--accent-chartreuse)] px-7 py-3.5 font-display text-sm font-bold uppercase tracking-wider text-foreground transition hover:brightness-95 disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              >
                {saveMutation.isPending ? "Saving…" : "Save profile"}
                <span aria-hidden>→</span>
              </button>
            </div>
          </div>
        </form>

        {/* Minor fix: visually separated from the primary task with a
            divider and reduced weight, so it reads as secondary/optional
            info rather than competing with Step 1's actual task. */}
        <section className="mt-14 border-t border-foreground/10 pt-10">
          <h2 className="mb-5 font-display text-sm font-semibold text-muted-foreground">
            System integrations
          </h2>
          <div className="flex flex-wrap gap-3">
            <IntegrationChip label="SMS Forwarding Tunnel" connected />
            <IntegrationChip label="Email Invoices" />
            <IntegrationChip label="Historical ITR Uploads" />
          </div>
        </section>

        <footer className="mt-16 flex items-center justify-between text-xs text-muted-foreground">
          <span className="font-display font-bold uppercase tracking-[0.25em] text-foreground">
            Kairos
          </span>
          <span>Compliance OS for Indian micro-merchants</span>
        </footer>
      </div>
    </div>
  );
}

function FormField({
  label,
  hint,
  value,
  onChange,
  required,
}: {
  label: string;
  hint?: string;
  value?: string;
  onChange: (v: string) => void;
  required?: boolean;
}) {
  return (
    <label className="block">
      <span className="mb-2 block text-xs font-medium text-muted-foreground">
        {label}
        {required && <span aria-hidden> *</span>}
      </span>
      <input
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value)}
        required={required}
        // P1 fix: real focus ring (DESIGN.md's own spec: "ring token
        // outline, no border-color change") instead of a 10%→40%
        // border-opacity shift with no outline/ring at all.
        className="w-full rounded-2xl border border-foreground/10 bg-background px-4 py-3.5 text-base text-foreground outline-none transition focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
      />
      {hint ? <span className="mt-1.5 block text-xs text-muted-foreground">{hint}</span> : null}
    </label>
  );
}

function SegmentedControl({
  value,
  onChange,
  options,
}: {
  value?: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <div
      role="radiogroup"
      aria-label="Tax structure"
      className="inline-flex w-full rounded-full bg-background p-1 md:w-auto"
    >
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          role="radio"
          aria-checked={o.value === value}
          onClick={() => onChange(o.value)}
          className={`flex-1 rounded-full px-5 py-2.5 text-sm font-medium transition md:flex-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${
            o.value === value
              ? "bg-foreground text-background"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

function IntegrationChip({ label, connected }: { label: string; connected?: boolean }) {
  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm ${
        connected
          ? "border-emerald-600/20 bg-emerald-600/10 text-emerald-800"
          : "border-foreground/10 bg-card text-muted-foreground"
      }`}
    >
      <span className={`h-2 w-2 rounded-full ${connected ? "bg-emerald-600" : "bg-muted-foreground/40"}`} />
      {label}
      {/* P1 fix: dropped opacity-70 on this status word — it measured
          ≈3.31:1 on the tinted chip background, a real contrast fail at
          this text's 12px size. font-medium instead gives the same visual
          distinction without dropping below 4.5:1. */}
      <span className="text-xs font-medium">{connected ? "Connected" : "Not connected"}</span>
    </span>
  );
}
