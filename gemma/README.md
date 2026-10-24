# Gemma 4 on our own Cloud Run GPU

The app normally calls Gemma 4 through the Gemini API, where the model writes about a minute of hidden
reasoning before each answer. This folder runs the same model (`gemma4:26b`, via Ollama) on a Cloud Run
**NVIDIA L4 GPU** with thinking turned off, so chat answers start in seconds.

- **Private:** the service doesn't allow public calls. The website signs each request with its own Google identity.
- **Scales to zero:** it only costs money while it's awake (about $1/hour on the L4), paid from Cloud credits.
  The tools page wakes it when the chat comes into view (`/api/gemma/warm`); a cold start takes a few minutes,
  and during that time the chat uses the Gemini API instead.
- **Fallback:** if the GPU is asleep, starting or failing, `backend/gemma_gpu.py` gives up after 20 seconds and
  the app uses the Gemini API, so the chat never breaks.

## Build and deploy

```bash
gcloud builds submit gemma --tag us-east4-docker.pkg.dev/gen-lang-client-0995218526/cloud-run-source-deploy/gemma4:26b --region us-east4 --machine-type e2-highcpu-8 --disk-size 100
gcloud run deploy gemma4 --image us-east4-docker.pkg.dev/gen-lang-client-0995218526/cloud-run-source-deploy/gemma4:26b --region us-east4 --no-allow-unauthenticated --gpu 1 --gpu-type nvidia-l4 --no-gpu-zonal-redundancy --cpu 4 --memory 16Gi --no-cpu-throttling --concurrency 4 --max-instances 1 --min-instances 0 --timeout 600
```

Then let the website call it, and point the website at it:

```bash
gcloud run services add-iam-policy-binding gemma4 --region us-east4 --member serviceAccount:875094537886-compute@developer.gserviceaccount.com --role roles/run.invoker
gcloud run services update clear-house --region us-east4 --update-env-vars GEMMA_GPU_URL=<gemma4 service URL>
```

To stop all GPU spending, remove `GEMMA_GPU_URL` from clear-house (the app goes back to the Gemini API) or delete the `gemma4` service.
