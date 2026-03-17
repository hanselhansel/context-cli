# Serve Modes

Context CLI provides three ways to serve markdown to AI agents that send `Accept: text/markdown` requests. All modes use the same markdown engine pipeline under the hood.

## How Content Negotiation Works

When an AI agent (or any HTTP client) sends a request with the `Accept: text/markdown` header, the serve mode intercepts the request, fetches or generates the HTML response, converts it through the markdown engine, and returns clean markdown with `Content-Type: text/markdown`.

Regular browser requests (without the `Accept: text/markdown` header) receive the original HTML unchanged.

## Reverse Proxy

The reverse proxy runs as a standalone server that sits in front of your existing website.

### Usage

```bash
context-cli serve --upstream https://example.com --port 8080
```

### Configuration

| Flag | Default | Description |
|---|---|---|
| `--upstream` | (required) | The origin server URL to proxy |
| `--port` | `8080` | Port to listen on |
| `--host` | `0.0.0.0` | Host to bind to |

### How it works

1. Client sends request to the proxy
2. Proxy checks for `Accept: text/markdown` header
3. If present: fetch upstream HTML, convert to markdown, return `text/markdown`
4. If absent: proxy the request to upstream unchanged

## ASGI Middleware (FastAPI / Starlette)

Add markdown serving to any ASGI application as middleware.

### Usage

```python
from fastapi import FastAPI
from context_cli.middleware import MarkdownASGIMiddleware

app = FastAPI()
app = MarkdownASGIMiddleware(app)
```

### Configuration

The middleware accepts optional keyword arguments:

```python
app = MarkdownASGIMiddleware(
    app,
    exclude_paths=["/api/", "/static/"],  # paths to skip conversion
)
```

### How it works

1. Middleware intercepts incoming requests
2. Checks for `Accept: text/markdown` header
3. If present: lets the inner app generate the HTML response, converts it to markdown
4. If absent: passes the request through unchanged

## WSGI Middleware (Django / Flask)

Add markdown serving to any WSGI application as middleware.

### Usage with Flask

```python
from flask import Flask
from context_cli.middleware import MarkdownWSGIMiddleware

app = Flask(__name__)
app.wsgi_app = MarkdownWSGIMiddleware(app.wsgi_app)
```

### Usage with Django

```python
# In your wsgi.py
from context_cli.middleware import MarkdownWSGIMiddleware

application = MarkdownWSGIMiddleware(application)
```

### How it works

Same as the ASGI middleware, but for synchronous WSGI applications.

## Web Server Config Generation

For production deployments, you can generate web server configuration snippets that handle `Accept: text/markdown` routing at the server level:

```bash
context-cli generate-config nginx
context-cli generate-config apache
context-cli generate-config caddy
```

Each generates a config snippet that detects `Accept: text/markdown` in incoming requests and routes them to a local Context CLI markdown endpoint.

### Nginx example

```nginx
map $http_accept $markdown_backend {
    default         "";
    "~text/markdown" http://127.0.0.1:8081;
}

server {
    listen 80;

    location / {
        if ($markdown_backend) {
            proxy_pass $markdown_backend;
        }
        proxy_pass http://upstream_backend;
    }
}
```

## Choosing a Serve Mode

| Mode | Best for | Requires code changes |
|---|---|---|
| Reverse proxy | Quick setup, any origin | No |
| ASGI middleware | FastAPI / Starlette apps | Yes (one line) |
| WSGI middleware | Django / Flask apps | Yes (one line) |
| Web server config | Production, high traffic | No (server config only) |
