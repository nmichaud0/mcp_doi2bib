# Setup Instructions with Authentication

## Step 1: Generate an Authentication Token

Run this in your terminal:
```bash
openssl rand -hex 32
```

This generates a secure random token like: `a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6`

## Step 2: Add Token to Railway

1. In Railway, go to your service
2. Click **Variables** tab
3. Add variable:
   - Name: `AUTH_TOKEN`
   - Value: (paste your generated token)
4. Railway will auto-redeploy

## Step 3: Update Your GitHub Repo

Replace these files:
- `server-http-auth.py` → rename to `server-http.py`
- `Dockerfile`

## Step 4: Add to Claude Web

1. Go to Claude.ai → Settings → Integrations
2. Click "+ Add Custom Integration"
3. Name: `DOI to BibTeX`
4. URL: `https://mcpdoi2bib-production.up.railway.app/sse`
5. It will ask for authentication - enter your AUTH_TOKEN
6. Click Connect

## Optional: No Authentication (Not Recommended)

If you don't want authentication (anyone can use your server):
- Just don't set the AUTH_TOKEN variable in Railway
- The server will work without authentication

But this means anyone who finds your URL can use your server.
