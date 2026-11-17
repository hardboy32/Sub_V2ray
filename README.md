# Sub V2ray

Public V2Ray subscription aggregator that collects configured sources, normalizes and deduplicates supported proxy links, checks endpoint reachability, ranks candidates, and publishes a stable subscription URL.

## Planned behavior

- Refresh source subscriptions every 30 minutes.
- Decode plain-text and Base64 subscription responses.
- Parse VLESS, VMess, Trojan, and Shadowsocks links.
- Deduplicate normalized links.
- Check endpoint TCP reachability with bounded concurrency and timeouts.
- Keep at most 200 best-scoring candidates.
- Publish a stable public subscription endpoint.
- Preserve the last known-good output if a refresh fails.

## Important testing limitation

A deployment on Railway tests reachability from Railway's network, not from Iranian mobile/fixed-line networks. An Iran-specific result must only be published after a real test agent is available inside Iran. The initial version must not label foreign-region tests as Iran tests.

## Configuration

Set `SOURCES` to a comma- or newline-separated list of subscription URLs in Railway Variables. Optional variables:

- `REFRESH_MINUTES` (default: `30`)
- `MAX_RESULTS` (default: `200`)
- `TEST_CONCURRENCY` (default: `40`)
- `CONNECT_TIMEOUT` (default: `4`)
- `PUBLIC_BASE_URL` (used to display the stable subscription URL)

## Deployment

Deploy this repository as a Docker service on Railway. The app exposes `/sub/all`, `/health`, and `/status`.

## Security and operational notes

The subscription is intentionally public. Anyone with its URL can retrieve the selected proxy links. Do not add private source URLs or credentials unless you intend to expose their resulting proxy configurations publicly. Respect source owners' terms and rate limits.

The first release uses endpoint reachability and latency as a screening signal; it does not claim a full end-to-end VPN throughput test. A real Iranian-network test requires a separate agent running on an Iranian connection.
