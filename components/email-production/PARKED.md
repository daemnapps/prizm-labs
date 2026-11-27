# Parked — real, and out of scope for now

Set aside 2026-08-27 so the campaign path could be settled first. None of this
is dropped; it is waiting.

## Delivery

Building the email in the platform, uploading images, links and tracking, the
QA gate, scheduling. Mechanical, and almost all of it is calls the connected
Klaviyo tools can already make. Worth nothing until there is a calendar
producing sends to deliver.

## Feedback

What each send earned, recorded against the slot that asked for it. Subjects
onto the ledger so ground is not spent twice. Winners back into the swipe file
as sources. This is the loop that makes the system compound instead of just
repeat — and it is empty in every lane, not only email.

## Flows

A different product from a campaign. Installed once, sends forever on a
trigger. Set up quarterly and adjusted rather than composed monthly.
Eventually flows per avatar.

Two constraints already known and worth keeping:

- **Flows cannot be built by API at all** — a human assembles them in the
  platform. A machine can produce the spec, the copy and the template; it
  cannot install the flow.
- <brand> currently runs **three live Browse Abandonment flows and three live
  Abandoned Checkout flows.** Before flows are designed, that has to be
  resolved — nobody can currently say how many emails one abandoning customer
  receives.

## The account's own facts

The derived numbers — orders by month, day and hour, the 308-line subject
ledger, the segment inventory — live in `calendar/brands/` and are pulled by
`calendar/derive.py` and `calendar/ledger.py`. They are not part of the three
steps, but the calendar reads them.
