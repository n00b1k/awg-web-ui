# AmneziaWG Web UI

A comprehensive web-based management interface for AmneziaWG VPN servers. This service provides an easy-to-use web UI to create, manage, and monitor WireGuard VPN servers with AmneziaWG's advanced obfuscation features.
All server configuration is done via web interface or via API endpoints.

<img src="screenshot2.png" alt="Web UI screenshot" width="50%"/>
<img src="screenshot.png" alt="Web UI screenshot" width="50%"/>

## Features

- **Web-based Management**: Intuitive UI for managing VPN servers and clients
- **AmneziaWG Integration**: Full support for AmneziaWG's obfuscation features
- **Client Management**: Generate and download client configurations. Suspend and reactivate clients on live server.
- **Real-time Monitoring**: Live server status and connection monitoring
- **Auto-start**: Automatic server startup on container restart
- **IPTables Automation**: Automatic firewall configuration
- **Custom values**: MTU and other connection settings can be customized
- **QR code**: Client can be viewed, copied and downloaded via text, file or QR code
- **Config view**: Both servers' and clients' configs can be viewed directly from UI
- **Auto SSL support**: Automatic SSL cert deployment
- **AWG 1.5 and 2.0 support**: I1-I5 and S3-S4 values can be customized
- **Client data**: Clients' traffic, last handshake and IP are displayed and auto-refreshed

## Docker Deployment

Official docker image repository: https://hub.docker.com/r/n00b1k/awg-web-ui

### Environment Variables

| Variable              | Default           | Description                                                                                       |
| --------------------- | ----------------- | ------------------------------------------------------------------------------------------------- |
| `ADMIN_USERNAME`      | `-`               | Username for basic auth in the app                                                                |
| `ADMIN_PASSWORD_HASH` | `-`               | Password for basic auth in the app                                                                |
| `DEFAULT_MTU`         | `1280`            | Default MTU value for new servers. Effective only for api requests. For UI management set via UI. |
| `DEFAULT_SUBNET`      | `10.0.0.0/24`     | Default subnet for new servers. Effective only for api requests. For UI management set via UI.    |
| `DEFAULT_PORT`        | `51820`           | Default port for new servers. Effective only for api requests. For UI management set via UI.      |
| `DEFAULT_DNS`         | `8.8.8.8,1.1.1.1` | Default DNS servers for clients. Effective only for api requests. For UI management set via UI.   |
| `IP_LIST`             | `-`               | A list of IP addresses or IP ranges to allow connections from.                                    |

### Docker Run Example

```bash
docker run --rm n00b1k/awg-web-ui:1.3.5 gph 'password'
```

```bash
docker run -d \
  --name awg-web-ui \
  -p 5000:5000 \
  -p 51820:51820/udp \
  -v /opt/awg-web-ui:/etc/amnezia \
  -v /opt/awg-web-ui/certs:/app/certs \
  -e ADMIN_USERNAME=user \
  -e ADMIN_PASSWORD_HASH='$2b$12$ePJa8CpQ2T2h2ISjqNeec.ARH7kK/VyIpf6KhPhMgSDRwM.r2mmxa' \
  -e DEFAULT_MTU=1420 \
  -e DEFAULT_SUBNET=192.168.99.0/24 \
  -e DEFAULT_PORT=51820 \
  -e DEFAULT_DNS="1.1.1.1,9.9.9.9" \
  --cap-add=NET_ADMIN \
  --cap-add SYS_MODULE \
  --sysctl net.ipv4.ip_forward=1 \
  --sysctl net.ipv4.conf.all.src_valid_mark=1 \
  --device /dev/net/tun \
  --restart unless-stopped \
  n00b1k/awg-web-ui:1.3.5
```

## Protection by IP address

You can protect your webserver by limiting connections to the it through the list of IP address(es) and IP range(s). To enable it you need to provide env variable `IP_LIST` at docker container run, e.g.
`-e IP_LIST="100.200.101.201, 50.100.10.0/24"`

## Obfuscation Parameters

AmneziaWG supports advanced traffic obfuscation to bypass censorship and DPI (Deep Packet Inspection).

## Parameter Reference

| Parameter | Range          | Default | Recommended | Description                           |
| --------- | -------------- | ------- | ----------- | ------------------------------------- |
| `Jc`      | 1-128          | 8       | 4-12        | Controls connection pattern frequency |
| `Jmin`    | 1-1279         | 8       | 8           | Minimum padding size for packets      |
| `Jmax`    | Jmin+1 to 1280 | 80      | 80          | Maximum padding size for packets      |
| `S1`      | 1-1132         | 50      | 15-150      | Obfuscation pattern parameter 1       |
| `S2`      | 1-1188         | 60      | 15-150      | Obfuscation pattern parameter 2       |
| `H1`      | 5-2147483647   | 1000    | Unique      | Header obfuscation parameter 1        |
| `H2`      | 5-2147483647   | 2000    | Unique      | Header obfuscation parameter 2        |
| `H3`      | 5-2147483647   | 3000    | Unique      | Header obfuscation parameter 3        |
| `H4`      | 5-2147483647   | 4000    | Unique      | Header obfuscation parameter 4        |
| `MTU`     | 1280-1440      | 1280    | 1280-1420   | Maximum Transmission Unit             |

## Detailed Parameter Explanation

### Jc (Connection Parameter)

- **Purpose**: Controls how frequently connection patterns are applied
- **Lower values**: More frequent pattern application (more obfuscation, lower performance)
- **Higher values**: Less frequent pattern application (less obfuscation, better performance)
- **Recommended**: 4-12 for optimal balance

### Jmin and Jmax (Padding Parameters)

- **Jmin**: Minimum random padding added to each packet
- **Jmax**: Maximum random padding added to each packet
- **Relationship**: Jmax must be greater than Jmin
- **Note**: Values are constrained by MTU (typically 1280 for basic internet)

### S1 and S2 (Pattern Parameters)

- **Purpose**: Define obfuscation patterns for traffic shaping
- **Constraints**:
  - S1 ≤ 1132 (1280 - 148 = 1132)
  - S2 ≤ 1188 (1280 - 92 = 1188)
  - S1 + 56 ≠ S2 (must be different with margin)
- **Recommended**: 15-150 for effective obfuscation

### H1-H4 (Header Parameters)

- **Purpose**: Unique identifiers for header obfuscation
- **Requirement**: All four values must be unique
- **Recommended**: Use random values in range 1000-1000000

### MTU (Maximum Transmission Unit)

- **Purpose**: Defines maximum packet size
- **Standard Internet**: 1280 (safe for all connections)
- **Better Performance**: 1420-1440 (may have compatibility issues)
- **Trade-off**: Higher MTU = better performance but potential fragmentation

# Support

The NO support provided as well as no regular updates are planned. Found issues can be fixed if free time permits.
