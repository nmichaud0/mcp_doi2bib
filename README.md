# DOI to BibTeX MCP Server

An MCP (Model Context Protocol) server that converts DOIs to BibTeX format using the official DOI content negotiation API.

## How It Works

This server uses [DOI content negotiation](https://citation.doi.org/docs.html) to fetch BibTeX entries directly from `doi.org`. When you provide a DOI, it makes an HTTP request with the `Accept: application/x-bibtex` header to get the bibliographic data in BibTeX format.

## Deployment Options

### Option 1: Free Railway Deployment (Recommended for Claude Web)

Railway offers a free tier perfect for hosting this MCP server:

1. **Create a Railway account** at https://railway.app (free)

2. **Create a new project**:
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Connect your GitHub account
   - Push these files to a GitHub repo
   - Select your repository

3. **Railway will automatically**:
   - Detect the Dockerfile
   - Build and deploy your server
   - Give you a public URL like `https://your-app.up.railway.app`

4. **Add to Claude Web**:
   - Go to Settings > Integrations in Claude.ai
   - Click "+ Add Custom Integration"
   - Enter name: "DOI to BibTeX"
   - Enter URL: `https://your-app.up.railway.app/sse`
   - Click Connect

**Railway Free Tier**: $5/month credit, enough for thousands of DOI conversions

### Option 2: Claude Desktop (Local)

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Add to your MCP settings file:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "doi-to-bibtex": {
      "command": "python",
      "args": ["/absolute/path/to/doi-to-bibtex-mcp.py"]
    }
  }
}
```

3. Restart Claude Desktop

## Usage

Once connected, ask Claude to convert DOIs:

**Example requests:**
- "Convert DOI 10.1038/nature12373 to BibTeX"
- "Get BibTeX for https://doi.org/10.1126/science.1157784"
- "I need the BibTeX entry for doi:10.1103/PhysRevLett.104.198101"

The server accepts DOIs in multiple formats:
- Just the identifier: `10.1234/example`
- With doi: prefix: `doi:10.1234/example`
- Full URL: `https://doi.org/10.1234/example`

## Files Included

- `server-http.py` - HTTP/SSE version for Railway
- `doi-to-bibtex-mcp.py` - stdio version for Claude Desktop
- `Dockerfile` - Railway deployment configuration
- `requirements.txt` - Python dependencies

## Alternative Free Hosting Options

- **Render**: https://render.com (free tier available)
- **Fly.io**: https://fly.io (free tier available)
- **Replit**: https://replit.com (free tier available)

All work similarly - push your code, get a public URL, add to Claude.

## Data Source

This server uses the official DOI content negotiation service, which redirects to the appropriate registration agency (Crossref, DataCite, etc.) for each DOI. The data comes directly from publishers and registration agencies.

## License

MIT
