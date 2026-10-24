# Deploying to Google Cloud Run

Clear House runs on Cloud Run in **us-east4 (Northern Virginia)**, in the `gen-lang-client-0995218526`
("Default Gemini Project") Google Cloud project.

## How the hosted copy differs

- The Gemma key is stored in **Secret Manager** as `gemini-api-key`, never in the code or the container.
- `CLEARHOUSE_READ_ONLY=1`: Cloud Run's disk resets on every restart, so the hosted copy doesn't run the
  open-data review queue or the listing take-downs. Run those locally and push the data.
- `WARM_EXAMPLES=1`: the example questions on the resources page are answered when the server starts.
- At most 2 instances run at once, so costs stay small.

## Redeploy after changes

Push your changes, then from the project folder:

```bash
gcloud run deploy clear-house --source . --region us-east4 \
  --allow-unauthenticated --set-secrets GEMINI_API_KEY=gemini-api-key:latest \
  --max-instances 2 --memory 1Gi --cpu 1 --timeout 300
```

`.gcloudignore` keeps `.env`, `.venv` and `.git` out of the upload.

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
