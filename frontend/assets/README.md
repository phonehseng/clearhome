# Page styles and scripts

Each page's HTML file holds its markup. Its CSS and JavaScript live here, one file per job, and the page links them in the
order they apply. Order matters: a later stylesheet wins over an earlier one, and a script can use what an earlier
script on the same page defined (they share one global scope, as inline scripts did).

Shared files stay at the top of `frontend/`: `site-header.css` and `site-header.js` (the header on every page),
`interface.css` (text selection, image credits), `listing-map.js` (the map) and `rental-labels.js` (rent wording).

| Folder | Page | Files, in load order |
|---|---|---|
| `app/` | Tools page, `/app` (`index.html`) | `arrival.js` clears the dark-blue arrival from the front page's intro (runs before first paint) · `base.css` layout, forms, chat, listings, map and cards · `readability.css` the readability pass, which overrides `base.css` · `background.js` the background scene · `listings.js` Explore Rentals: cards, filters, favorites, sharing and Gemma's sort · `find.js` the find form and the Ask Gemma chat · `walk.js` walking-distance search · `help-tips.js` help tips beside the checkboxes · `back-to-top.js` |
| `home/` | Front page, `/` (`about.html`) | `home.css` all styles · `main.js` hero, scenery, pinned scroll scenes, flip cards, map video and the tonight chat · `scroll-extras.js` progress bar and scroll effects · `coverage.js` the "What's in the list" counts · `github-card.js` live GitHub stats · `get-started.js` the Get Started intro |
| `resources/` | `/resources` | `resources.css` · `resources.js` the chat, programs and rentals |
| `google-cloud/` | `/google-cloud` | `google-cloud.css` · `motion.js` scroll entrances and the diagram's request dot |
| `review/` | `/review` | `review.css` · `review.js` verify, flag or hide listings |

Flask serves this folder at `/assets/` with `Cache-Control: no-cache`, so browsers check for a newer copy on each visit
(a quick "not modified" when nothing changed). Edit a file and deploy; there is no build step or version number to bump.

To add a file, put it in the page's folder and add a `<link rel="stylesheet" href="/assets/<page>/<file>.css">` or
`<script src="/assets/<page>/<file>.js"></script>` where it should load. Keep `<script>` tags without `defer` or
`async` unless the code is safe to run later, since several scripts expect the markup above them to exist already.
