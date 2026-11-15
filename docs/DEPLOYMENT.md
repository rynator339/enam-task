# Deploy FINN from GitHub

## Single-service assessment deployment

1. Create an empty GitHub repository in your account. From the prepared local FINN checkout, run the commands below after substituting your repository URL. The local checkout already has a main branch and commits. If using the source ZIP, unzip it first and run `git init -b main`, `git add .` and `git commit -m "FINN submission"`.
2. In Render, choose **New → Blueprint**, connect that GitHub repository and review the root `render.yaml`. It declares one Docker web service on the free plan. Apply the Blueprint if that plan is available in your account. Keep the Docker build context at the repository root.
3. Leave model keys unset for the evidence-only submission. Both the phone app and API share the assigned HTTPS origin. A separate frontend service, CORS setting and public API key are unnecessary.
4. Check the GitHub Actions validation run, including the Linux Docker smoke test. Once the service is healthy, open its public URL in a signed-out browser on a phone. Open `/api/health` on that same origin. A fresh instance should report database connected, 21 company records (18 watched), 103 announcements, five documents and AI disabled.
5. In the app open **Latest saved week**, open a filing and its source, change an alert threshold, then open **Compare the evidence**. Confirm 20–22%, 21.1%, met, and two source pages. Ask the prefilled research question. The answer should identify evidence-only mode. Check the GitHub and conversation links as the reviewer will see them.

```sh
git remote add origin YOUR_GITHUB_REPOSITORY_URL
git push -u origin main
```

The free service may cold-start. Its writable filesystem is ephemeral. Restarting on a fresh disk reloads the included snapshot and discards later imports. This suffices to replay the assessment example. To retain new imports set a PostgreSQL connection string as a backend-only `DATABASE_URL`. Use the same database for any external refresh worker. The GitHub ingestion workflow needs the repository secret `DATABASE_URL` to write to the deployed database. Without persistent storage, leave scheduled refresh disabled or run the CLI on the active service.

## Docker locally

```sh
docker build -t finn .
docker run --rm -p 8000:8000 finn
```

Open http://localhost:8000. The image runs one API process. A fresh local run without a volume starts from the snapshot. The underlying static export and same-origin API were tested together on macOS. Building the Linux Docker image and checking the assigned public URL remain release steps.

The original split deployment is also supported. Deploy `apps/api` using its Dockerfile, set its allowed `CORS_ORIGINS` to the web origin, build `apps/web` with `NEXT_PUBLIC_API_BASE_URL` set to the API HTTPS origin and serve its `out` folder. Set all hosted-model credentials on the API service.

[Render Blueprint configuration reference](https://render.com/docs/blueprint-spec)
