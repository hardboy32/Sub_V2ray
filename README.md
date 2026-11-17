# Sub V2ray

Public V2Ray subscription aggregator that collects configured sources, deduplicates supported proxy links, checks endpoint reachability, ranks candidates, and publishes a stable subscription URL.

## Behavior

- Refresh source subscriptions every 30 minutes.
- Decode plain-text and Base64 subscription responses.
- Parse VLESS, VMess, Trojan, and Shadowsocks links.
- Remove exact duplicate links.
- Check endpoint TCP reachability with bounded concurrency and timeouts.
- Keep at most 200 reachable candidates, ranked by TCP response time.
- Publish a stable public subscription endpoint.
- Preserve the last known-good output if a refresh fails.

## Railway Variables

Add source URLs as separate Railway Variables. Use the numbers `1` through `100` as variable names and put one subscription URL in each value:

```text
1 = https://example.com/sub1
2 = https://example.com/sub2
3 = https://github.com/example/configs
...
100 = https://example.com/sub100
```

You do not need to fill every number; empty or missing numbers are ignored. The app reads these variables on startup and on every refresh. The old `SOURCES` variable (comma- or newline-separated URLs) is also supported for compatibility.

Optional variables:

- `REFRESH_MINUTES` (default: `30`)
- `MAX_RESULTS` (default: `200`)
- `TEST_CONCURRENCY` (default: `40`)
- `CONNECT_TIMEOUT` (default: `4`)

## Endpoints

- `/sub/all` — Base64 subscription output for clients such as v2rayNG, v2rayN, and Hiddify.
- `/health` — health check.
- `/status` — source and refresh status.

## Testing limitation

Railway checks TCP reachability from the Railway deployment region, not from Iranian mobile/fixed-line networks. This is only a basic endpoint check, not a full V2Ray handshake or real throughput benchmark. Do not treat it as an Iran test. An Iran-specific result requires a real test agent running on an Iranian connection.

## Security

The subscription endpoint is public. Anyone who obtains its URL can retrieve the selected proxy links. Do not add private source URLs or credentials unless you intend the resulting proxy configurations to be publicly accessible. Respect source owners' terms and rate limits.

## Deployment

Deploy this repository as a Docker service on Railway.
