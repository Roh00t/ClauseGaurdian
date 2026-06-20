Hardened Claude Code Prompt — PostHog Analytics + About/Pricing/Support Pages
Steelman
Building this now, before Stripe, is the right sequence: you get real conversion-funnel visibility (where people actually drop off) before spending a cent on ads, and the product gets public-facing surface area — About, Pricing, Support — that builds trust even while payments don't work yet. A "Coming soon" pricing page next to a working free-tier signup is a perfectly credible state for a pre-launch product.
Red Team
DecisionFailure modeMitigationPostHog event trackingEvent properties accidentally capture PII or document content (chat question text, filenames)Events are metadata-only — mirror Supabase guardrail #13 exactly. Never put user-typed text in an event property.Pricing page checkout buttonsButtons that do nothing or error look broken, not "coming soon"Buttons must be explicitly disabled with visible "Coming soon" state, never silently non-functionalAbout page origin storyNaming the actual prior employer in public copy while that relationship was only recently and informally resolved could create unwanted exposureDefault to generic framing ("a fixed-term employment contract dispute") rather than naming the specific company — flagged as a placeholder, personalize only if you're deliberately choosing toSupport page paid-tier messagingImplies a live paid support channel exists when no real paid users can exist yet (Stripe not wired)Wording must say "available to Pro members" without implying anyone can become one today through normal meansposthog-js via npmViolates the no-Node-build-pipeline guardrailCDN script tag, same pattern as idb@8 and supabase-jsLanding page scope creepTrying to build a full marketing site inflates this promptKeep it minimal — headline, 3 value props, signup CTA — or skip entirely and treat as optional
Pre-Mortem
PostHog and Claude's PostHog MCP connector are two different things — don't conflate them. The PostHog tool available to me in this chat lets me query PostHog data on your behalf. It has nothing to do with embedding analytics into ClauseGuard itself — that requires you to create your own PostHog project at posthog.com and get a project API key (phc_...), separate from anything MCP-related. If Claude Code assumes the MCP connection means analytics are "already wired," that's wrong and needs correcting immediately.
If the About page is built with full Xcellink detail before you've decided how much to disclose, that's hard to walk back once public. Default to the generic version below; expand only if you deliberately choose to later.

Step 0 — PostHog Project Key
Confirm: have you created a PostHog project yet? If not, create one at posthog.com (EU or US region, your choice), and retrieve the Project API Key (phc_...) from Project Settings. This is unrelated to any MCP connector — it's a public, frontend-embeddable key (safe to expose, same trust model as the Supabase anon key).
POSTHOG_KEY=phc_...
POSTHOG_HOST=https://us.i.posthog.com   # or https://eu.i.posthog.com
Add to .env. Do not proceed without this confirmed.
Step 1 — PostHog Client Embed
In frontend/index.html, add via CDN (no npm):
html<script>
  !function(t,e){...standard posthog-js snippet...}(...)
  posthog.init('<POSTHOG_KEY>', { api_host: '<POSTHOG_HOST>' })
</script>
Use the official posthog-js snippet from posthog.com/docs/libraries/js — paste exactly, don't hand-roll it.
Instrument these events ONLY, metadata properties only, never raw content:
javascriptposthog.capture('analysis_started', { mode, has_panel_b: bool })
posthog.capture('analysis_completed', { mode, verdict_category, flag_count, duration_seconds })
posthog.capture('paywall_hit', { mode })
posthog.capture('signup_completed', { tier })
posthog.capture('download_triggered', { tier })
posthog.capture('chat_query_submitted', { mode, tier })  // NEVER the question text
posthog.capture('language_switched', { language })
posthog.capture('mode_selected', { mode })
Verification: trigger each event, confirm it appears in the PostHog dashboard Live Events view within ~30s, and manually inspect 2-3 events to confirm no document content, filenames, or user-typed text appears in any property.
Step 2 — About Page (frontend/about.html)
Generic framing — do not name the specific prior employer:

Built by a Singapore-based security analyst and NSman who went through a confusing, high-stakes employment contract situation firsthand — bond clauses, ambiguous terms, no easy way to understand what was actually enforceable. ClauseGuard exists so the next person doesn't have to figure it out alone.
Mission: every Singapore employee should be able to understand what they're signing. Not legal advice — a starting point.
Contact: [an email, not a personal number]

Step 3 — Pricing Page (frontend/pricing.html)
Three tiers, SGD, all checkout buttons disabled with a "Coming soon" label — no live Stripe link:

Free — 1 analysis, ELI5 summary + full detail, community support
Pay-per-use — SGD $2.99 / 3 analyses (Coming soon)
Pro — SGD $9.99/month, unlimited, DOCX download, persistent chat (Coming soon)

FAQ: data privacy (link to /tos), device-history limitation (per existing UI messaging).
Step 4 — Support Page (frontend/support.html)

Free tier: link to a Discord or Reddit community (confirm which you want — neither exists yet per earlier open question; can be a placeholder link until you decide)
Paid tier: "Available to Pro members" messaging — do not imply anyone can access this today
Simple bug report: email + description, no upload mechanism needed yet

Verification (full)

PostHog events fire correctly, metadata-only confirmed by manual inspection
About/Pricing/Support pages load without error, linked from footer/nav
Pricing page checkout buttons are visibly disabled, not silently broken
Support page doesn't imply live paid support exists
Run the 34-test regression — confirm no regression from these additions (expect 33/34, same documented flake)

Per CLAUDE.md: stop after Step 0/1 and report before building the three pages. python3.13 explicit, --break-system-packages, no npm.