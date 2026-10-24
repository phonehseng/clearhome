# Clear House

A housing assistant frontend for Northern Virginia, built with React and Vite. Clear House supports affordable housing search, emergency resources, saved resources, and informational lease/listing checks.

## Run locally

```sh
npm install
npm run dev
```

`npm run build` creates the production frontend in `dist/`. `npm test` checks resource verification, filtering, urgency ordering, and limited text checks.

## Verified resources

`data/resources.json` uses the team's existing schema (see `data/README.md`). Placeholder and unverified entries are excluded. Displayed entries require `verified: true`, a valid `last_verified` date, an HTTPS `source_url`, a name, and an address.

The frontend supports `affordable_listing`, `housing_authority`, `rental_assistance`, and `emergency_shelter`. Optional `monthly_rent` (number) supports strict budget filtering; `accessible: true` supports accessibility filtering. Unknown rent or accessibility never counts as a match for a corresponding filter. An optional `urgent: true` places emergency resources first.

Location searches currently match the address text; include Northern Virginia in the address for regional search. This does not implement geocoding. Prices, eligibility, and availability must be confirmed with providers. Saved IDs persist on this device.

## Current scope

This is a frontend foundation. Gemma 4 is not connected; the assistant explicitly provides preset navigation guidance. Lease/listing checks use limited browser-local patterns and are informational, not legal advice or a determination of safety. They do not provide a full lease explanation. Saved resource IDs persist in local storage on the current browser; lease text is not stored or sent to a server. No accounts or uploads are implemented.

## Git workflow

For each completed change, use the requested sequence:

```sh
git add -A
git commit -m "Describe what changed"
git pull
git push
```
