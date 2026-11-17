# Sub V2ray

Public V2Ray subscription aggregator. Railway collects configured sources, removes duplicate links, performs a basic reachability check from its own network, and publishes the full selected list as one stable subscription. The user's own V2Ray client performs the final latency test and lets the user choose the best node for their network.

## How it works

1. Railway fetches the configured subscription sources every 30 minutes.
2. It decodes plain-text and Base64 responses and extracts VLESS, VMess, Trojan, and Shadowsocks links.
3. Exact duplicate links are removed.
4. Railway checks whether each node's host and port accept a TCP connection from the Railway region. This is only a preliminary filter.
5. Up to 200 reachable links are published together in the subscription.
6. The user imports or updates that subscription in a compatible client, runs that client's latency test, and selects the best node for their own connection.

**Important:** the service does not choose one universal best node. Network routes differ by user, ISP, country, and time. The complete selected list is returned so each user can test it from their own device and network.

## Railway Variables

Add source URLs as separate Railway service Variables. Use names `link_1` through `link_20`, with one subscription URL in each value:

```text
link_1 = https://example.com/sub1
link_2 = https://example.com/sub2
link_3 = https://example.com/sub3
...
link_20 = https://example.com/sub20
```

You do not need to fill every number; missing or empty variables are ignored. Older names `SOURCE_1` through `SOURCE_20` and numeric names `1` through `20` are also accepted for backward compatibility. The old `SOURCES` variable (comma- or newline-separated URLs) is also supported.

Optional variables:

- `REFRESH_MINUTES` (default: `30`)
- `MAX_RESULTS` (default: `200`)
- `TEST_CONCURRENCY` (default: `40`)
- `CONNECT_TIMEOUT` (default: `4`)

## Public endpoints

- `/sub/all` — full Base64 subscription for clients such as v2rayNG, v2rayN, and Hiddify.
- `/sub` — short alias for the same subscription.
- `/health` — health check.
- `/status` — source, refresh, and testing status.

After deploying on Railway, copy the public domain and append `/sub/all` to create the subscription URL. In the client, add it as a subscription and use the client's update and latency-test functions. Client UI labels differ by app and version.

## What is and is not tested

- Railway tests only basic TCP reachability from the Railway deployment region.
- The user's V2Ray client performs the final node latency test from the user's own device and internet connection.
- This service does not perform a full Xray handshake or a real download/upload throughput benchmark.
- There is no dedicated Iranian test agent, and Railway results must not be described as Iran-tested.

## Security

The subscription endpoint is public. Anyone who obtains its URL can retrieve the selected proxy links. Do not add private source URLs or credentials unless you intend the resulting proxy configurations to be publicly accessible. Respect source owners' terms and rate limits.

## Deployment

Deploy this repository as a Docker service on Railway.
