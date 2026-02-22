"""Middleware config generator -- Nginx/Apache/Caddy snippets for markdown routing."""

from __future__ import annotations


def generate_nginx_config(upstream: str, port: int = 8080) -> str:
    """Generate nginx config snippet for Accept: text/markdown routing."""
    return f"""\
# Nginx: Route Accept: text/markdown to Context CLI markdown proxy
# Add this inside your server {{ }} block

location / {{
    # Check if the client wants markdown
    set $markdown_proxy "";
    if ($http_accept ~* "text/markdown") {{
        set $markdown_proxy "yes";
    }}

    # If Accept: text/markdown, proxy to Context CLI
    if ($markdown_proxy = "yes") {{
        proxy_pass http://127.0.0.1:{port};
    }}

    # Otherwise, serve normally
    proxy_pass {upstream};
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}}
"""


def generate_apache_config(upstream: str, port: int = 8080) -> str:
    """Generate Apache config snippet for Accept: text/markdown routing."""
    return f"""\
# Apache: Route Accept: text/markdown to Context CLI markdown proxy
# Enable required modules: mod_rewrite, mod_proxy, mod_proxy_http, mod_headers
#   a2enmod rewrite proxy proxy_http headers

<VirtualHost *:80>
    # Enable rewrite engine
    RewriteEngine On

    # Route Accept: text/markdown to Context CLI proxy
    RewriteCond %{{HTTP:Accept}} text/markdown
    RewriteRule ^(.*)$ http://127.0.0.1:{port}$1 [P,L]

    # Default: proxy to upstream
    ProxyPass / {upstream}/
    ProxyPassReverse / {upstream}/

    # Forward original headers
    ProxyPreserveHost On
    RequestHeader set X-Forwarded-Proto expr=%{{REQUEST_SCHEME}}
</VirtualHost>
"""


def generate_caddy_config(upstream: str, port: int = 8080) -> str:
    """Generate Caddy config snippet for Accept: text/markdown routing."""
    return f"""\
# Caddy: Route Accept: text/markdown to Context CLI markdown proxy
# Add this to your Caddyfile

:80 {{
    # Route markdown requests to Context CLI proxy
    @markdown header Accept *text/markdown*
    reverse_proxy @markdown 127.0.0.1:{port}

    # Default: proxy to upstream
    reverse_proxy {upstream}
}}
"""


_GENERATORS = {
    "nginx": generate_nginx_config,
    "apache": generate_apache_config,
    "caddy": generate_caddy_config,
}


def generate_middleware_config(
    server_type: str,
    upstream: str,
    port: int = 8080,
) -> str:
    """Generate web server config for markdown routing.

    Args:
        server_type: One of "nginx", "apache", "caddy"
        upstream: Upstream URL to proxy
        port: Port for the markdown proxy

    Raises:
        ValueError: If server_type is not supported.
    """
    generator = _GENERATORS.get(server_type.lower())
    if generator is None:
        supported = ", ".join(sorted(_GENERATORS))
        raise ValueError(
            f"Unsupported server type: {server_type!r}. "
            f"Supported: {supported}"
        )
    return generator(upstream, port)
