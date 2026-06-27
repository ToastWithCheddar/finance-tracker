# TLS Termination Options (INFRA-NGINX-001)

The repo's `nginx/nginx.conf` is now configured to serve a 443 block when
`/etc/nginx/ssl/fullchain.pem` and `privkey.pem` are mounted. Three viable
ways to provision those certs in production:

## Comparison

| Option | Setup effort | Auto-renew | Operational cost | Fits stack? |
|---|---|---|---|---|
| **Caddy** as edge proxy | Low | Yes (built in) | None | Replace nginx; fewest moving parts. |
| **nginx + acme-companion** | Medium | Yes (sidecar) | Small | Drop-in alongside existing nginx. |
| **Cloud LB (ALB/CloudFront/GCLB) terminates TLS** | Medium | Yes (managed) | Cloud-only | Best for k8s / managed deploys. |
| Manual certbot + cron | Low | Manual until wired | Higher (renewal misses) | Only for dev / single host. |

## Recommendation

For a small self-hosted deployment, **swap nginx for Caddy** at the edge.
For a managed cloud deployment, **terminate TLS at the load balancer** and
keep nginx as an internal-only router with HTTP listeners.

## Option A — Caddy (preferred for self-host)

```yaml
# docker-compose.prod.yml — replace the nginx service with:
caddy:
  image: caddy:2.8-alpine
  restart: unless-stopped
  ports: ["80:80", "443:443"]
  volumes:
    - ../../infra/Caddyfile:/etc/caddy/Caddyfile:ro
    - caddy_data:/data
    - caddy_config:/config
  networks: [finance-internal, finance-edge]
```

Minimal `Caddyfile`:

```caddy
example.com {
  encode gzip
  header {
    Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
    X-Frame-Options "DENY"
    X-Content-Type-Options "nosniff"
    Referrer-Policy "strict-origin-when-cross-origin"
    Permissions-Policy "geolocation=(), microphone=(), camera=()"
  }
  @api path /api/* /ws
  reverse_proxy @api backend:8000
  reverse_proxy frontend:80
}
```

Caddy handles ACME automatically — no sidecar required. Trade-off: replaces
nginx's rate-limiting (`limit_req_zone`) which would have to be reimplemented
with `caddy-ratelimit` plugin.

## Option B — nginx + acme-companion

```yaml
# add alongside the existing nginx service:
nginx-proxy:
  image: nginxproxy/nginx-proxy:1.6
  ports: ["80:80", "443:443"]
  volumes:
    - /var/run/docker.sock:/tmp/docker.sock:ro
    - certs:/etc/nginx/certs
    - vhost:/etc/nginx/vhost.d
    - html:/usr/share/nginx/html

acme-companion:
  image: nginxproxy/acme-companion:2.4
  volumes_from: [nginx-proxy]
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock:ro
    - acme:/etc/acme.sh
  environment:
    - DEFAULT_EMAIL=ops@example.com
```

## Option C — cloud LB termination

Terminate at AWS ALB / GCP HTTPS LB / Cloudflare. nginx in the stack becomes
internal-only, listens on 80, and trusts `X-Forwarded-Proto https` from the
LB. Easiest for k8s-style deployments; no cert management inside the cluster.

## Decision checklist

- Public DNS pointed at the host? -> Caddy or acme-companion both fine.
- Behind Cloudflare / cloud LB? -> Option C; remove the 443 server block.
- Need cert rotation alerts? -> CloudWatch / Caddy logs + Prometheus exporter.
