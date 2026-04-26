### run (tag = 1.1.7, 1.2.4, 1.2.5)

docker run --rm n00b1k/awg-web-ui:1.2.5 gph 'password'
-e ADMIN_PASSWORD_HASH='$2b$12$ePJa8CpQ2T2h2ISjqNeec.ARH7kK/VyIpf6KhPhMgSDRwM.r2mmxa'

```
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
  n00b1k/awg-web-ui:1.2.5
```

### run (tag = 1.1.4)

```
docker run -d \
  --name awg-web-ui \
  -p 5000:5000 \
  -p 51820:51820/udp \
  -v /opt/awg-web-ui:/etc/amnezia \
  -v /opt/awg-web-ui/certs:/app/certs \
  -e ADMIN_USERNAME=user \
  -e ADMIN_PASSWORD=password \
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
  n00b1k/awg-web-ui:1.1.4
```

Place manual certificates key.pem and cert.pem in the catalog
/opt/awg-web-ui/certs

### run (tag = 1.0.9)

```
  docker run -d \
  --name awg-web-ui \
  -p 5000:5000 \
  -p 51820:51820/udp \
  -v amnezia:/etc/amnezia \
  -e ADMIN_USERNAME=user \
  -e ADMIN_PASSWORD=password \
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
  n00b1k/awg-web-ui:1.0.9
```

### run (tag = 1.0.2, 1.0.3)

```
docker run -d \
  --name awg-web-ui \
  -p 9090:9090 \
  -p 51820:51820/udp \
  -v amnezia:/etc/amnezia \
  -e NGINX_PORT=9090 \
  -e NGINX_USER=user \
  -e NGINX_PASSWORD=password \
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
  n00b1k/awg-web-ui:1.0.3
```
