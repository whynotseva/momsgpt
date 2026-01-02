# MomsVPN Audit Report (2 Jan 2026)

## 1. Executive Summary
- The web admin panel is exposed without any authentication or CSRF protection; anyone who reaches `/admin` can block/unblock users, reset traffic, or extend keys directly against Marzban.
- All Marzban-facing HTTP clients run with `verify=False` and no host allow‑list, which makes the bot/API vulnerable to TLS stripping, credential theft, and SSRF if the URL is tampered with.
- Subscription links are sent to a third‑party Happ encryption API over the public Internet, leaking every user’s private VLESS URL to an external service.
- Billing webhook ingestion accepts unsigned JSON and would treat any POST as a legitimate YooKassa event.
- Missing Xray configuration in the repo prevents verifying UDP support, fallback transports, and SNI rotation—current outages with mobile games likely stem from datacenter IP reputation and/or missing UDP/XUDP support.

## 2. Critical Vulnerabilities
| Severity | Finding | Evidence | Recommendation |
| --- | --- | --- | --- |
| Critical | Admin web UI has no auth; destructive actions exposed at `/admin` | `app/admin/main.py` wires routes with no auth middlewares and `/admin` view renders dashboard; `app/admin/routes/keys.py` exposes POST actions to block/unblock/reset/extend users without any guard. | Protect the admin app with proper auth (at minimum HTTP auth or Telegram SSO), CSRF for form POSTs, and network ACLs; disable `/admin` in production until authentication is enforced. |
| Critical | TLS verification disabled for all Marzban calls (bot, API, admin) | `app/api/services/xray.py` creates `httpx.AsyncClient(..., verify=False)` and reuses it for all requests; `app/admin/services/marzban.py` and `/sub` proxy also set `verify=False`. | Enforce certificate verification, pin expected host, and fail closed on TLS errors; remove `verify=False`, configure CA bundle/Let’s Encrypt, and add host allow‑listing. |
| Critical | Subscription URLs exfiltrated to third‑party encryption service | `app/bot/utils/crypto.py` posts raw VLESS URLs to `https://crypto.happ.su/api.php` and returns the remote result. | Move encryption client‑side or self-host the service; until then, do not send subscription URLs to third parties and gate the feature behind explicit user consent. |
| High | Billing webhook trusts any payload | `app/api/routers/billing.py` accepts POST at `/billing/webhook/yookassa` and forwards JSON to `BillingService` without signature/header validation. | Validate YooKassa signatures/idempotence keys, restrict source IPs, and reject unsigned/unknown events; add retry-safe processing. |

## 3. Code Security Findings
| Severity | Issue | Evidence | Recommendation |
| --- | --- | --- | --- |
| High | Hard-coded admin list in bot; no env-based control or audit logging | `app/bot/handlers/admin.py` defines `ADMIN_IDS = [44054166]` and `is_admin` simply checks membership. | Read admin IDs from env/DB, add structured audit logs for admin actions, and fail closed when the list is empty. |
| High | Admin API calls use shared bearer token without refresh/expiry handling | `app/admin/services/marzban.py` caches `_token` forever and never handles 401 refresh. | Add token expiry detection/re-auth and central retry logic; include minimal scopes if Marzban supports them. |
| Medium | Subscription proxy logs full User-Agent and client IP without consent and with `verify=False` | `app/api/routers/subscription.py` logs device info and proxies with disabled TLS. | Minimize logged PII, rotate logs, and enable TLS verification; add token format validation to avoid abuse. |
| Medium | No rate limiting or anti-spam for bot commands/callbacks | All handlers in `app/bot/handlers/start.py`/`admin.py` accept unlimited requests. | Add aiogram throttling middleware and per-user cooldowns, especially for admin mutations. |
| Medium | Payment creation auto-creates users from unauthenticated requests | `app/api/routers/billing.py` will create a DB user if the Telegram ID is unknown. | Require authenticated callers or signed bot-originated requests before billing; validate Telegram ID ownership. |
| Low | HTTP clients and DB engine created globally but never closed | `MarzbanService` stores a long-lived `httpx.AsyncClient` without shutdown; FastAPI startup creates tables on boot. | Close AsyncClient on shutdown, add lifespan events, and remove auto-migrate behavior in production. |

## 4. Code Quality & Maintainability
- **Error handling gaps:** Many HTTP calls swallow exceptions and return `None`, making failures silent (`MarzbanService.get_user`, `APIClient.get_subscription`). Add typed error propagation and user-facing messages.
- **Logging consistency:** Mix of `print` and logger usage (`app/bot/main.py`). Standardize on structured logging with request IDs and avoid logging secrets or full URLs.
- **Configuration management:** Critical values are spread across code (hard-coded admin IDs, Happ API URL). Centralize in settings with validation and defaults.
- **Testing:** No automated tests or linters present; SQLite echo logging is enabled by default, which will leak queries in production logs.

## 5. VPN Configuration Assessment
- The repository does not include `xray_config.json` or Marzban inbound definitions beyond the tag reference (`"VLESS_TCP_REALITY"`), so best-practice verification is impossible from code alone.
- To restore game connectivity and harden against DPI (2026 context), implement:
  - **Reality + XUDP + Vision flow:** enable `flow: xtls-rprx-vision`, `sockopt.mark`, and `tproxy`/`xudp` for UDP-heavy games.
  - **SNI and fingerprint rotation:** rotate between `apple.com`, `www.apple.com`, `dropbox.com`, `www.microsoft.com`; set `fingerprint: chrome/safari` with randomized order.
  - **Ports and fallbacks:** serve Reality on 8443/7443 and add WebSocket fallback behind TLS/CDN (Cloudflare) to hide origin IP.
  - **Outbound controls:** enforce `domainStrategy: UseIP` for games, block LAN/metadata leaks, and ensure firewall allows UDP 443/8443.
  - **Key hygiene:** rotate `privateKey`/`shortId` regularly; keep them out of repo and restrict filesystem perms.

## 6. Investigation: Instagram works, games fail
- **Likely root causes:** (a) the server IP `31.130.130.238` is datacenter/hosting-flagged, so Supercell blocks it; (b) UDP or XUDP is not enabled on the inbound/outbound path; (c) routing may bypass or fragment game traffic due to MTU.
- **Validation steps:**
  1) IP reputation: `curl http://ip-api.com/json/31.130.130.238?fields=hosting,proxy,tor` and compare with competitor IPs; move to less-detected ASNs or Cloudflare WARP/ residential egress.
  2) UDP path: run `nc -u game-server.supercell.com 9339` over the tunnel and trace packets on the server (`tcpdump -ni any udp port 9339`); enable `xudp` if drops occur.
  3) Routing/DNS: confirm all DNS and game domains go through the tunnel (dnsleaktest.com, `ip route` policy), and ensure no bypass rules for *.supercell.com.
  4) MTU: test `ping -M do -s 1300 game-server.supercell.com` to identify fragmentation; tune MTU/MPP settings in Xray.
- **Competitive comparison (LunarVPN clues):** they use Reality+Vision on port 8443 with Apple/Dropbox SNI and providers (H2nexus, Servers Tech) that are less aggressively flagged; mirroring this plus UDP enablement should restore game traffic.

## 7. Roadmap (prioritized)
1) Lock down `/admin` (auth + CSRF + network ACL) and rotate Marzban credentials/TLS settings immediately.
2) Remove `verify=False`, add pinned CA/hostname validation, and close HTTP clients cleanly; add retries and timeouts.
3) Stop sending subscription URLs to external services; implement in-app encryption or ship raw links with user opt-in.
4) Secure billing webhook with signature verification and source filtering; add idempotent transaction handling.
5) Add bot rate limiting, admin audit logging, and environment-driven admin lists.
6) Publish hardened Xray config with UDP/XUDP, SNI rotation, and Cloudflare WS fallback; consider WARP or residential egress for gaming users.
7) Add automated tests/linters and move configuration into validated settings classes.
