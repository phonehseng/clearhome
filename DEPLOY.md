# Deploying to Google Cloud Run

Clear House runs on Cloud Run in **us-east4 (Northern Virginia)**, in the `gen-lang-client-0995218526`
("Default Gemini Project") Google Cloud project.

## How the hosted copy differs

- The Gemma and Google Maps keys are stored in **Secret Manager** (`gemini-api-key`, `google-maps-server-key`,
  `google-maps-browser-key`), never in the code or the container.
- `CLEARHOUSE_READ_ONLY=1`: Cloud Run's disk resets on every restart, so the hosted copy doesn't run the
  open-data review queue or the listing take-downs. Run those locally and push the data.
- `WARM_EXAMPLES=1`: the example questions on the resources page are answered when the server starts.
- At most 2 instances run at once, so costs stay small.

## Redeploy after changes

Push your changes, download the listing photos so they ship with the app, then deploy from the project folder:

```bash
python backend/listing_photos.py
```


```bash
gcloud run deploy clear-house --source . --region us-east4 \
  --allow-unauthenticated \
  --set-secrets GEMINI_API_KEY=gemini-api-key:latest,GOOGLE_MAPS_SERVER_API_KEY=google-maps-server-key:latest,GOOGLE_MAPS_BROWSER_API_KEY=google-maps-browser-key:latest \
  --max-instances 2 --memory 1Gi --cpu 1 --timeout 300
```

`.gcloudignore` keeps `.env`, `.venv` and `.git` out of the upload.

## Automatic deploys (every push to main)

`cloudbuild.yaml` downloads the listing photos, builds the container and deploys it to Cloud Run. A Cloud Build
trigger runs it whenever `main` changes on GitHub, so nobody has to run `gcloud run deploy` by hand. The service keeps
its secrets, env vars and limits; only the code changes. No keys are stored in GitHub.

One-time setup, from the project folder (needs the Owner or Editor role on the project):

```bash
PROJECT=$(gcloud config get-value project)
NUMBER=$(gcloud projects describe $PROJECT --format='value(projectNumber)')
gcloud services enable cloudbuild.googleapis.com run.googleapis.com artifactregistry.googleapis.com

# Let the build deploy to Cloud Run (both accounts, since which one Cloud Build uses depends on the project's age).
for SA in $NUMBER-compute@developer.gserviceaccount.com $NUMBER@cloudbuild.gserviceaccount.com; do
  for ROLE in roles/run.admin roles/iam.serviceAccountUser roles/artifactregistry.writer roles/logging.logWriter; do
    gcloud projects add-iam-policy-binding $PROJECT --member=serviceAccount:$SA --role=$ROLE --condition=None --quiet >/dev/null
  done
done
```

Then connect GitHub and create the trigger in the console (the GitHub connection needs a browser sign-in):

1. Open **Cloud Build → Triggers** (console.cloud.google.com/cloud-build/triggers), pick region **us-east4**
   (or **global**), and click **Connect repository**. Choose **GitHub (Cloud Build GitHub App)**, sign in, and select
   `phonehseng/clearhouse`.
2. Click **Create trigger**: name `clear-house-deploy`, event **Push to a branch**, branch `^main$`,
   configuration **Cloud Build configuration file**, location `cloudbuild.yaml`. Service account: the
   compute default (`…-compute@developer.gserviceaccount.com`). Save.
3. Click **Run** on the trigger once to deploy the current `main` and check it works (about 4–6 minutes).
   Builds and their logs are under **Cloud Build → History**.

After that, merging a pull request or pushing to `main` updates the live site a few minutes later. Pushes to other
branches don't deploy. The manual command above still works for a one-off deploy.

## Automatic listing upkeep (every day)

`.github/workflows/listing-upkeep.yml` keeps the listings current without anyone having to remember. Every day at
5:30 am Eastern it:

1. pulls new open-data records into the review queue (`backend/sources.py`);
2. has Gemini look for new listings in the next two areas of a rotation (`backend/discover.py`): it thinks first, searches
   with Google Search, then rereads each source page and quotes it, and code checks every quote is really on the page.
   A find goes live only if it comes from the property's own site or a public agency, every fact was confirmed, the
   address maps inside our service area and the record passes the catalog checks. It's labeled as added automatically
   and flagged on `/review`. Everything else waits in `data/candidates.json` (`python backend/review.py list`);
3. renews listings their providers still offer (another week, only with a quote found on the provider's own page) and
   takes down ones they don't (`backend/freshness.py --limit 60`, soonest review date first);
4. checks the catalog and runs the tests, commits and pushes any data changes to `main`, and redeploys the site.

The run summary (Actions tab) lists what was found, published, queued, renewed and taken down.

One-time setup, from the project folder:

```bash
gh secret set GEMINI_API_KEY        # paste the Gemini key when asked
```

For the redeploy step, a service account that can deploy, saved as the `GCP_SA_KEY` secret (without it the job still
commits and pushes; deploy by hand):

```bash
SA=clear-house-upkeep@gen-lang-client-0995218526.iam.gserviceaccount.com
gcloud iam service-accounts create clear-house-upkeep --display-name "Listing upkeep deploys"
for ROLE in roles/run.admin roles/iam.serviceAccountUser roles/cloudbuild.builds.editor roles/artifactregistry.writer \
            roles/storage.admin roles/serviceusage.serviceUsageConsumer; do
  gcloud projects add-iam-policy-binding gen-lang-client-0995218526 --member=serviceAccount:$SA --role=$ROLE --condition=None --quiet >/dev/null
done
gcloud iam service-accounts keys create key.json --iam-account=$SA
gh secret set GCP_SA_KEY < key.json && rm key.json
```

- Google Search grounding has a small free daily limit; for a dependable daily run, turn on billing for the Gemini key's
  project. When the limit is reached, that area is simply searched again on a later run.
- To send every new find to the review queue instead of publishing: `gh variable set AUTO_PUBLISH --body 0`.
- Run it now: `gh workflow run listing-upkeep.yml` (or Actions → Listing upkeep → Run workflow).

## Change the key

```bash
sed -n 's/^GEMINI_API_KEY=//p' .env | tr -d '\r\n' | gcloud secrets versions add gemini-api-key --data-file=-
```

Then redeploy so the service picks up the new version.

## First-time setup on a new machine

Install the [Google Cloud CLI](https://cloud.google.com/sdk/docs/install) (it needs Python 3.10+), then:

```bash
gcloud auth login
gcloud config set project gen-lang-client-0995218526
```
