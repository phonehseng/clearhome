# Listing existence check, third pass — October 25, 2026

The first two passes checked each record against its official source and then tested every source link. This
third pass asks a different question with a different source of truth: does each place actually exist and operate today?
It covers every community the app serves (385 communities, 419 records), using `backend/existence_audit.py`:

1. **Google Places.** Is there a place with a matching name at our address (or within half a mile), and is it
   operating or permanently closed? Confidential domestic-violence shelter locations were never looked up.
2. **The place's own pages.** Do its source page and website load and name it? Pages that block automated visitors were
   recorded as blocked and never worked around.
3. **A person checked the rest** by web search (county, city and property sources), since a blocked page or a
   program with no storefront isn't evidence either way.

## Results

| Result | Communities |
|---|---|
| Confirmed by Google Maps **and** their own page | 274 |
| Confirmed by Google Maps (operating) | 53 |
| Confirmed by their own page naming them | 47 |
| Not confirmed automatically; then confirmed by web search | 10 |
| Google Maps says permanently closed | 1 (renamed, see below) |
| **Confirmed to exist** | **385 of 385** |

## The eleven that needed a person

| Place | Why the script couldn't confirm it | What the search found |
|---|---|---|
| Glen Arbor (Woodbridge) | Google lists "Glen Arbor Apartments" as permanently closed | Renovated and **renamed Elevations One**, same 209 units, now all at 60% of area median income (Prince William County IDA, AGM Financial). Record renamed and the street spelling fixed (Jeffries Road); flagged on `/review` to find the leasing phone |
| Margot (Alexandria) | City PDF source; new building | Carr Properties' 425 Montgomery St; the city lists 16 set-aside units, first phase expected in December |
| Parc Meridian (Alexandria) | City PDF source; site blocks checks | 750 Port St; on the city's May 2026 affordable-unit list |
| Potomac West (Alexandria) | City PDF source | 3620 Edison St; its site lists a different phone (flagged on `/review` to call both) |
| Purcellville East (Purcellville) | County PDF source | 110 N 16th St, 46-unit tax-credit property; our phone matches |
| Little River Glen (Fairfax) | Google matched the senior center next door (temporarily closed) | 120 senior one-bedrooms at 4001 Barker Ct; the apartments are open |
| Sullivan House Family Shelter (Arlington) | Site blocks checks; address kept private | Bridges to Independence family shelter; intake through Arlington DHS, 703-228-1300 |
| David's Place (Alexandria) | Page loads but is a general page | Carpenter's Shelter day center, 930 N. Henry St |
| City of Fairfax ADU rentals | A program, no storefront | City ordinance (2020), administered by the Fairfax County housing authority |
| Arlington DHS emergency rent help | County page blocks checks | Arlington's eviction-prevention page, 703-228-1300 |
| Arlington committed affordable units | County page blocks checks | The county's monthly CAF list (October 2026 list posted) |
| City of Fairfax shelter access | County page blocks checks | Fairfax County's 703-222-0880 intake serves City of Fairfax residents |

## What this doesn't establish

A place existing isn't a vacancy, a rent quote or eligibility. Those still need a call to the provider, and the
records say so.
