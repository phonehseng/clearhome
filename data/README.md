# Resource list

`resources.json` is the list of real housing help the assistant is allowed to recommend. The AI only picks from this file, so it can't invent places or phone numbers.

## Rules

- Copy details from the organization's **own website**, not a third-party page.
- Never guess. If you can't find a field, leave it as `null`.
- When you've confirmed an entry, set `verified` to `true` and `last_verified` to today's date (YYYY-MM-DD).
- Delete the `PLACEHOLDER` entries once you've added real ones. Aim for 15 to 20 total.
- Only list public organizations, never individuals' contact details.

## Types

`emergency_shelter`, `rental_assistance`, `legal_aid`, `affordable_listing`, `food_support`, `housing_authority`, `other`

## Fields

| Field | Meaning |
|---|---|
| `id` | Short unique name, e.g. `new-river-shelter` |
| `name` | Organization or program name |
| `type` | One of the types above |
| `address`, `phone`, `website`, `hours` | Contact details |
| `who_it_serves` | Who qualifies (families, adults, income limits) |
| `cost` | Free, or the price |
| `accessible` | `true`, `false`, or `null` if unknown |
| `requirements` | ID, referral, income proof, etc. |
| `source_url` | The page you took the information from |
| `last_verified` | Date you checked it |
| `verified` | `true` only after you checked it |
