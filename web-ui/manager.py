import os
import json
import subprocess
import tempfile
import uuid
import base64
import random
import requests
import threading
import time
import ipaddress
from config import (
    CONFIG_DIR, WIREGUARD_CONFIG_DIR, CONFIG_FILE,
    DEFAULT_MTU, DEFAULT_SUBNET, DEFAULT_PORT, DNS_SERVERS,
    ENABLE_OBFUSCATION, AUTO_START_SERVERS, DEFAULT_I1, DEFAULT_I2,
    DEFAULT_I3, DEFAULT_I4, DEFAULT_I5
)

class AmneziaManager:
    def __init__(self, socketio_instance):
        self.socketio = socketio_instance
        self.config = self.load_config()
        self.ensure_directories()
        self.public_ip = self.detect_public_ip()
        self.traffic_update_interval = 5
        self.suspend_update_interval = 60

        # Auto-start servers based on environment variable
        if AUTO_START_SERVERS:
            self.auto_start_servers()
            
        self.start_traffic_updates()
        self.start_suspension_checker()

    def ensure_directories(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        os.makedirs(WIREGUARD_CONFIG_DIR, exist_ok=True)
        os.makedirs('/var/log/amnezia', exist_ok=True)

    def detect_public_ip(self):
        """Detect the public IP address of the server"""
        try:
            # Try multiple services in case one fails
            services = [
                'http://ifconfig.me',
                'https://api.ipify.org',
                'https://ident.me'
            ]

            for service in services:
                try:
                    response = requests.get(service, timeout=5)
                    if response.status_code == 200:
                        ip = response.text.strip()
                        if self.is_valid_ip(ip):
                            print(f"Detected public IP: {ip}")
                            return ip
                except:
                    continue
        except Exception as e:
            print(f"Failed to detect public IP: {e}")
        return "YOUR_SERVER_IP"  # Fallback

    def is_valid_ip(self, ip):
        """Check if the string is a valid IP address"""
        try:
            parts = ip.split('.')
            if len(parts) != 4:
                return False
            for part in parts:
                if not 0 <= int(part) <= 255:
                    return False
            return True
        except:
            return False

    def auto_start_servers(self):
        """Auto-start servers that have config files and were running before"""
        print("Checking for existing servers to auto-start...")
        for server in self.config["servers"]:
            if os.path.exists(server['config_path']):
                current_status = self.get_server_status(server['id'])
                if current_status == 'stopped' and server.get('auto_start', True):
                    print(f"Auto-starting server: {server['name']}")
                    self.start_server(server['id'])

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        return {"servers": [], "clients": {}}

    def save_config(self):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.config, f, indent=2)

    def execute_command(self, command):
        """Execute shell command and return result"""
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"Command failed: {e}")
            return None

    def generate_wireguard_keys(self):
        """Generate real WireGuard keys"""
        try:
            private_key = self.execute_command("awg genkey")
            if private_key:
                public_key = self.execute_command(f"echo '{private_key}' | awg pubkey")
                return {
                    "private_key": private_key,
                    "public_key": public_key
                }
        except Exception as e:
            print(f"Key generation failed: {e}")

        # Fallback - generate random keys
        fake_private = base64.b64encode(os.urandom(32)).decode('utf-8')
        fake_public = base64.b64encode(os.urandom(32)).decode('utf-8')
        return {
            "private_key": fake_private,
            "public_key": fake_public
        }

    def generate_preshared_key(self):
        """Generate preshared key"""
        try:
            return self.execute_command("awg genpsk")
        except:
            return base64.b64encode(os.urandom(32)).decode('utf-8')

    def generate_obfuscation_params(self, mtu=None):
        if mtu is None:
            mtu = DEFAULT_MTU
    
        import random
        S1 = random.randint(15, min(150, mtu - 148))
        s2_candidates = [s for s in range(15, min(150, mtu - 92) + 1) if s != S1 + 56]
        S2 = random.choice(s2_candidates) if s2_candidates else 50
        S3 = random.randint(1, 256)
        S4 = random.randint(1, 32)
        Jmin = random.randint(4, mtu - 2)
        Jmax = random.randint(Jmin + 1, mtu)
        return {
            "Jc": random.randint(4, 12),
            "Jmin": Jmin,
            "Jmax": Jmax,
            "S1": S1,
            "S2": S2,
            "S3": S3,
            "S4": S4,
            "H1": random.randint(10000, 100000),
            "H2": random.randint(100000, 200000),
            "H3": random.randint(200000, 300000),
            "H4": random.randint(300000, 400000),
            "MTU": mtu
        }

    def create_wireguard_server(self, server_data):
        """Create a new WireGuard server configuration with environment defaults"""
        server_name = server_data.get('name', 'amnezia')
        port = server_data.get('port', DEFAULT_PORT)
        subnet = server_data.get('subnet', DEFAULT_SUBNET)
        mtu = server_data.get('mtu', DEFAULT_MTU)

        # Получить Public IP из запроса или использовать автоопределение
        custom_public_ip = server_data.get('public_ip', '').strip()
        if custom_public_ip:
            public_ip = custom_public_ip
        else:
            public_ip = self.public_ip

        # Get DNS servers from request or use environment default
        custom_dns = server_data.get('dns')
        if custom_dns:
            # Parse custom DNS from request
            if isinstance(custom_dns, str):
                dns_servers = [dns.strip() for dns in custom_dns.split(',') if dns.strip()]
            elif isinstance(custom_dns, list):
                dns_servers = custom_dns
            else:
                dns_servers = DNS_SERVERS
        else:
            dns_servers = DNS_SERVERS

        # Validate MTU
        if mtu < 1280 or mtu > 1440:
            raise ValueError(f"MTU must be between 1280 and 1440, got {mtu}")

        # Validate DNS servers
        for dns in dns_servers:
            if not self.is_valid_ip(dns):
                raise ValueError(f"Invalid DNS server IP: {dns}")

        # Fixed values for other settings
        enable_obfuscation = server_data.get('obfuscation', ENABLE_OBFUSCATION)
        auto_start = server_data.get('auto_start', AUTO_START_SERVERS)

        server_id = str(uuid.uuid4())[:6]
        interface_name = f"wg-{server_id}"
        config_path = os.path.join(WIREGUARD_CONFIG_DIR, f"{interface_name}.conf")

        # Generate server keys
        server_keys = self.generate_wireguard_keys()

        # Generate and use provided obfuscation parameters if enabled
        obfuscation_params = None
        if enable_obfuscation:
            if 'obfuscation_params' in server_data:
                obfuscation_params = server_data['obfuscation_params']
            else:
                obfuscation_params = self.generate_obfuscation_params(mtu)
                
        awg2_enabled = server_data.get('awg2', False)

        # Parse subnet for server IP
        subnet_parts = subnet.split('/')
        network = subnet_parts[0]
        prefix = subnet_parts[1] if len(subnet_parts) > 1 else "24"
        server_ip = self.get_server_ip(network)

        # Create WireGuard server configuration
        server_config_content = f"""[Interface]
PrivateKey = {server_keys['private_key']}
Address = {server_ip}/{prefix}
ListenPort = {port}
SaveConfig = false
MTU = {mtu}
"""

        # Add obfuscation parameters if enabled
        if enable_obfuscation and obfuscation_params:
            server_config_content += f"""Jc = {obfuscation_params['Jc']}
Jmin = {obfuscation_params['Jmin']}
Jmax = {obfuscation_params['Jmax']}
S1 = {obfuscation_params['S1']}
S2 = {obfuscation_params['S2']}
"""
            if awg2_enabled:
                server_config_content += f"""S3 = {obfuscation_params['S3']}
S4 = {obfuscation_params['S4']}
"""
            server_config_content += f"""H1 = {obfuscation_params['H1']}
H2 = {obfuscation_params['H2']}
H3 = {obfuscation_params['H3']}
H4 = {obfuscation_params['H4']}
"""
        server_config = {
            "id": server_id,
            "name": server_name,
            "protocol": "wireguard",
            "port": port,
            "status": "stopped",
            "interface": interface_name,
            "config_path": config_path,
            "server_public_key": server_keys['public_key'],
            "server_private_key": server_keys['private_key'],
            "subnet": subnet,
            "server_ip": server_ip,
            "mtu": mtu,
            "public_ip": public_ip,
            "custom_public_ip": bool(custom_public_ip),
            "obfuscation_enabled": enable_obfuscation,
            "awg2_enabled": awg2_enabled,
            "obfuscation_params": obfuscation_params,
            "auto_start": auto_start,
            "dns": dns_servers,
            "clients": [],
            "unbound_nat_ips": [],
            "created_at": time.time()
        }

        # Save WireGuard config file
        with open(config_path, 'w') as f:
            f.write(server_config_content)

        self.config["servers"].append(server_config)
        self.save_config()

        # Auto-start if enabled (from environment or request)
        if auto_start:
            print(f"Auto-starting new server: {server_name}")
            self.start_server(server_id)

        return server_config
    
    def apply_live_config(self, interface):
        """Apply the latest config to the running WireGuard interface using wg syncconf."""
        try:
            # Use bash -c to support process substitution
            command = f"bash -c 'awg syncconf {interface} <(awg-quick strip {interface})'"
            result = self.execute_command(command)
            if result is not None:
                print(f"Live config applied to {interface}")
                return True
            else:
                print(f"Failed to apply live config to {interface}")
                return False
        except Exception as e:
            print(f"Error applying live config to {interface}: {e}")
            return False

    def get_server_ip(self, network):
        """Get server IP from network (first usable IP)"""
        parts = network.split('.')
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.{parts[2]}.1"
        return "10.0.0.1"

    def get_new_client_ip(self, server_id):
        """Get client IP from server subnet"""
        server = next((s for s in self.config['servers'] if s['id'] == server_id), None)
        if not server:
            return False

        unbound_ips = server.get("unbound_nat_ips", [])
        if unbound_ips:
            unbound_ip = unbound_ips.pop(0)
            server["unbound_nat_ips"] = unbound_ips
            self.save_config()
            return unbound_ip

        subnet_str = server['subnet']
        network = ipaddress.ip_network(subnet_str)
    
        used_ips = {server['server_ip']}
        for client in server.get('clients', []):
            used_ips.add(client['client_ip'])

        for ip in network.hosts():
            ip_str = str(ip)
            if ip_str not in used_ips:
                return ip_str

        print(f"Subnet {subnet_str} is full! No available IPs.")
        return False

    def delete_server(self, server_id):
        """Delete a server and all its clients"""
        server = next((s for s in self.config['servers'] if s['id'] == server_id), None)
        if not server:
            return False

        # Stop the server if running
        if server['status'] == 'running':
            self.stop_server(server_id)

        # Remove config file
        if os.path.exists(server['config_path']):
            os.remove(server['config_path'])

        # Remove all clients associated with this server
        self.config["clients"] = {k: v for k, v in self.config["clients"].items()
                                if v.get("server_id") != server_id}

        # Remove the server
        self.config["servers"] = [s for s in self.config["servers"] if s["id"] != server_id]
        self.save_config()
        return True

    def add_wireguard_client(self, server_id, client_name, apply_i_settings=False, i_settings=None):
        """Add a client to a WireGuard server with optional I-settings"""
        server = next((s for s in self.config['servers'] if s['id'] == server_id), None)
        if not server:
            return None

        client_id = str(uuid.uuid4())[:6]

        # Generate client keys
        client_keys = self.generate_wireguard_keys()
        preshared_key = self.generate_preshared_key()

        # Assign client IP
        client_ip = self.get_new_client_ip(server_id)
        if not client_ip:
            return None

        # Process I-settings
        client_i_settings = {}
        if apply_i_settings:
            # Start with defaults
            client_i_settings = {
                'i1': DEFAULT_I1,
                'i2': DEFAULT_I2,
                'i3': DEFAULT_I3,
                'i4': DEFAULT_I4,
                'i5': DEFAULT_I5,
            }
            
            # Override with provided values
            if i_settings:
                for i in range(1, 6):
                    i_key = f'i{i}'
                    if i_key in i_settings and i_settings[i_key]:
                        client_i_settings[i_key] = i_settings[i_key]

        client_config = {
            "id": client_id,
            "name": client_name,
            "server_id": server_id,
            "server_name": server["name"],
            "status": "active",  # Set initial status to active
            "created_at": time.time(),
            "client_private_key": client_keys["private_key"],
            "client_public_key": client_keys["public_key"],
            "preshared_key": preshared_key,
            "client_ip": client_ip,
            "obfuscation_enabled": server["obfuscation_enabled"],
            "obfuscation_params": server["obfuscation_params"],
            "apply_i_settings": apply_i_settings,
            "i_settings": client_i_settings,
            "awg2_enabled": server.get("awg2_enabled", False)
        }

        # Add client to server config
        client_peer_config = f"""
# Client: {client_config['name']}
[Peer]
PublicKey = {client_keys['public_key']}
PresharedKey = {preshared_key}
AllowedIPs = {client_ip}/32
"""

        # Append client to server config file
        with open(server['config_path'], 'a') as f:
            f.write(client_peer_config)

        # Add to server's clients list
        server["clients"].append(client_config)

        # Also add to global clients dict
        self.config["clients"][client_id] = client_config.copy()
        
        self.save_config()
        
        # Apply live config if server is running
        if server['status'] == 'running':
            self.apply_live_config(server['interface'])
            
        print(f"Client {client_config['name']} added")

        config_content = self.generate_wireguard_client_config(server, client_config, include_comments=True)
        return client_config, config_content

    def delete_client(self, server_id, client_id):
        """Delete a client from a server and update the config file"""
        server = next((s for s in self.config['servers'] if s['id'] == server_id), None)
        if not server:
            return False

        client = next((c for c in server["clients"] if c["id"] == client_id), None)
        if not client:
            return False

        # Remove client from server's client list
        server["clients"] = [c for c in server["clients"] if c["id"] != client_id]

        # Remove from global clients dict
        if client_id in self.config["clients"]:
            del self.config["clients"][client_id]

        server.setdefault("unbound_nat_ips", []).append(client["client_ip"])

        # Rewrite the config file without the deleted client's [Peer] block
        self.rewrite_server_conf_without_client(server, client)

        self.save_config()

        # Apply live config if server is running
        if server['status'] == 'running':
            self.apply_live_config(server['interface'])
            
        print(f"Client {server['name']}:{client['name']} removed")

        return True
    
    def rewrite_server_conf_without_client(self, server, client):
        """Rewrite the server conf file without the specified client's [Peer] block"""
        if not os.path.exists(server['config_path']):
            return

        with open(server['config_path'], 'r') as f:
            lines = f.readlines()

        new_lines = []
        skip = False
        client_marker = f"# Client: {client['name']}"

        for line in lines:
            stripped = line.strip()

            # Start skipping when we find the client marker line
            if stripped == client_marker:
                skip = True
                continue

            # Stop skipping when we hit the next client marker line
            if skip and stripped.startswith("# Client:"):
                skip = False

            # If skipping, skip all lines until next client marker
            if skip:
                continue

            # Otherwise, keep the line
            new_lines.append(line)

        # Remove trailing blank lines if any
        while new_lines and new_lines[-1].strip() == '':
            new_lines.pop()

        with open(server['config_path'], 'w') as f:
            f.writelines(new_lines)

    def generate_wireguard_client_config(self, server, client_config, include_comments=True):
        """Generate WireGuard client configuration with optional I-settings"""
        config = ""
        
        # Add comments only if requested
        if include_comments:
            config = f"""# AmneziaWG Client Configuration
# Server: {server['name']}
# Client: {client_config['name']}
# Generated: {time.ctime(client_config['created_at'])}
# Server IP: {server['public_ip']}:{server['port']}
"""

        config += f"""[Interface]
PrivateKey = {client_config['client_private_key']}
Address = {client_config['client_ip']}/32
DNS = {', '.join(server['dns'])}
MTU = {server['mtu']}
"""

        # Add obfuscation parameters if enabled
        if client_config.get('obfuscation_enabled', False) and client_config.get('obfuscation_params'):
            params = client_config['obfuscation_params']
            config += f"""Jc = {params['Jc']}
Jmin = {params['Jmin']}
Jmax = {params['Jmax']}
S1 = {params['S1']}
S2 = {params['S2']}
"""
            if client_config.get('awg2_enabled', False):
                config += f"""S3 = {params['S3']}
S4 = {params['S4']}
"""
            config += f"""H1 = {params['H1']}
H2 = {params['H2']}
H3 = {params['H3']}
H4 = {params['H4']}
"""

        # Add I-settings if enabled and I1 is present
        if client_config.get('apply_i_settings', False):
            i_settings = client_config.get('i_settings', {})
            i1_value = i_settings.get('i1', '')
            
            if i1_value:  # Only add I-settings if I1 is present
                for i in range(1, 6):
                    i_value = i_settings.get(f'i{i}', '')
                    if i_value:  # Only add non-empty values
                        config += f"I{i} = {i_value}\n"
        
        config += f"""
[Peer]
PublicKey = {server['server_public_key']}
PresharedKey = {client_config['preshared_key']}
Endpoint = {server['public_ip']}:{server['port']}
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = 25
"""
        return config
    
    def update_client_i_settings(self, server_id, client_id, apply_i_settings=None, i_settings=None):
        """Update client I-settings"""
        server = next((s for s in self.config['servers'] if s['id'] == server_id), None)
        if not server:
            return None, "Server not found"

        # Find client in server's client list
        client = None
        for c in server["clients"]:
            if c["id"] == client_id:
                client = c
                break
        
        if not client:
            return None, "Client not found"
        
        # Update apply_i_settings if provided
        if apply_i_settings is not None:
            client['apply_i_settings'] = apply_i_settings
            if client_id in self.config["clients"]:
                self.config["clients"][client_id]['apply_i_settings'] = apply_i_settings
        
        # Process I-settings
        if i_settings is not None:
            new_i_settings = {}
            
            if apply_i_settings or client.get('apply_i_settings', False):
                # Start with defaults
                new_i_settings = {
                    'i1': DEFAULT_I1,
                    'i2': DEFAULT_I2,
                    'i3': DEFAULT_I3,
                    'i4': DEFAULT_I4,
                    'i5': DEFAULT_I5,
                }
                
                # Override with provided values
                for i in range(1, 6):
                    i_key = f'i{i}'
                    if i_key in i_settings and i_settings[i_key]:
                        new_i_settings[i_key] = i_settings[i_key]
                    elif client.get('i_settings', {}).get(i_key):
                        # Keep existing value
                        new_i_settings[i_key] = client['i_settings'][i_key]
            
            # Update both client objects
            client['i_settings'] = new_i_settings
            if client_id in self.config["clients"]:
                self.config["clients"][client_id]['i_settings'] = new_i_settings.copy()
        
        self.save_config()
        
        # Regenerate config
        config_content = self.generate_wireguard_client_config(server, client, include_comments=True)
        
        return client, config_content
    
    def suspend_client(self, server_id, client_id):
        """Suspend a client by removing its config from the main file"""
        server = next((s for s in self.config['servers'] if s['id'] == server_id), None)
        if not server:
            return False, "Server not found"

        client = next((c for c in server["clients"] if c["id"] == client_id), None)
        if not client:
            return False, "Client not found"

        # Create suspended configs directory if it doesn't exist
        suspended_dir = os.path.join(WIREGUARD_CONFIG_DIR, 'suspended')
        os.makedirs(suspended_dir, exist_ok=True)

        # Extract and save the client's peer block to suspended directory
        if os.path.exists(server['config_path']):
            with open(server['config_path'], 'r') as f:
                content = f.read()

            # Find the client's peer block
            client_marker = f"# Client: {client['name']}"
            lines = content.split('\n')
            
            peer_block = []
            in_peer_block = False
            for i, line in enumerate(lines):
                if line.strip() == client_marker:
                    in_peer_block = True
                    peer_block.append(line)
                elif in_peer_block and line.strip().startswith('[Peer]'):
                    peer_block.append(line)
                elif in_peer_block and line.strip() and not line.strip().startswith('#'):
                    peer_block.append(line)
                elif in_peer_block and not line.strip():
                    peer_block.append(line)
                    break

            if peer_block:
                suspended_path = os.path.join(suspended_dir, f"{client_id}.conf")
                with open(suspended_path, 'w') as f:
                    f.write('\n'.join(peer_block))

        # Remove client from server config
        self.rewrite_server_conf_without_client(server, client)
        
        # Update client status
        client['status'] = 'suspended'
        if client_id in self.config["clients"]:
            self.config["clients"][client_id]['status'] = 'suspended'

        self.save_config()

        # Apply live config if server is running
        if server['status'] == 'running':
            self.apply_live_config(server['interface'])

        return True, "Client suspended successfully"

    def activate_client(self, server_id, client_id):
        """Activate a suspended client by restoring its config"""
        server = next((s for s in self.config['servers'] if s['id'] == server_id), None)
        if not server:
            return False, "Server not found"

        client = next((c for c in server["clients"] if c["id"] == client_id), None)
        if not client:
            return False, "Client not found"

        # Check if client is suspended
        if client.get('status') != 'suspended':
            return False, "Client is not suspended"

        # Check for suspended config file
        suspended_dir = os.path.join(WIREGUARD_CONFIG_DIR, 'suspended')
        suspended_path = os.path.join(suspended_dir, f"{client_id}.conf")

        if not os.path.exists(suspended_path):
            return False, "Suspended config file not found"

        # Read the suspended config
        with open(suspended_path, 'r') as f:
            suspended_config = f.read()

        # Append config back to server config
        with open(server['config_path'], 'a') as f:
            f.write('\n' + suspended_config)

        # Remove suspended config file
        os.remove(suspended_path)

        # Update client status
        client['status'] = 'active'
        if client_id in self.config["clients"]:
            self.config["clients"][client_id]['status'] = 'active'

        self.save_config()

        # Apply live config if server is running
        if server['status'] == 'running':
            self.apply_live_config(server['interface'])

        return True, "Client activated successfully"
    
    def start_suspension_checker(self):
        """Start background task to check scheduled suspensions"""
        def check_suspensions():
            while True:
                try:
                    current_time = time.time()
                    for server in self.config['servers']:
                        for client in server['clients']:
                            suspend_at = client.get('suspend_at')
                            if suspend_at and client.get('status') == 'active':
                                if current_time >= suspend_at:
                                    # Reuse existing suspend endpoint logic
                                    self.suspend_client(server['id'], client['id'])
                                    print(f"Auto-suspended client {client['name']} at {time.ctime()}")
                except Exception as e:
                    print(f"Error checking suspensions: {e}")
                time.sleep(self.suspend_update_interval)
        
        suspension_thread = threading.Thread(target=check_suspensions, daemon=True)
        suspension_thread.start()

    def update_client_suspend_time(self, server_id, client_id, suspend_at=None):
        """Update client suspension time (without actually suspending)"""
        server = next((s for s in self.config['servers'] if s['id'] == server_id), None)
        if not server:
            return None, "Server not found"

        client = next((c for c in server["clients"] if c["id"] == client_id), None)
        if not client:
            return None, "Client not found"
        
        # Update suspension time
        if suspend_at:
            client['suspend_at'] = suspend_at
        else:
            client.pop('suspend_at', None)
        
        # Update global clients dict
        if client_id in self.config["clients"]:
            if suspend_at:
                self.config["clients"][client_id]['suspend_at'] = suspend_at
            else:
                self.config["clients"][client_id].pop('suspend_at', None)
        
        self.save_config()
        return client, "Suspension time updated"

    def setup_iptables(self, interface, subnet):
        """Setup iptables rules for WireGuard interface"""
        try:
            script_path = "/app/scripts/setup_iptables.sh"
            if os.path.exists(script_path):
                result = self.execute_command(f"{script_path} {interface} {subnet}")
                if result is not None:
                    print(f"iptables setup completed for {interface}")
                    return True
                else:
                    print(f"iptables setup failed for {interface}")
                    return False
            else:
                print(f"iptables script not found at {script_path}")
                return False
        except Exception as e:
            print(f"Error setting up iptables for {interface}: {e}")
            return False

    def cleanup_iptables(self, interface, subnet):
        """Cleanup iptables rules for WireGuard interface"""
        try:
            script_path = "/app/scripts/cleanup_iptables.sh"
            if os.path.exists(script_path):
                result = self.execute_command(f"{script_path} {interface} {subnet}")
                if result is not None:
                    print(f"iptables cleanup completed for {interface}")
                    return True
                else:
                    print(f"iptables cleanup failed for {interface}")
                    return False
            else:
                print(f"iptables cleanup script not found at {script_path}")
                return False
        except Exception as e:
            print(f"Error cleaning up iptables for {interface}: {e}")
            return False

    def start_server(self, server_id):
        """Start a WireGuard server using awg-quick with iptables setup"""
        server = next((s for s in self.config['servers'] if s['id'] == server_id), None)
        if not server:
            return False

        try:
            # Use awg-quick to bring up the interface
            result = self.execute_command(f"/usr/bin/awg-quick up {server['interface']}")
            if result is not None:
                # Setup iptables rules
                iptables_success = self.setup_iptables(server['interface'], server['subnet'])

                server['status'] = 'running'
                self.save_config()

                print(f"Server {server['name']} started successfully")
                if iptables_success:
                    print(f"iptables rules configured for {server['interface']}")
                else:
                    print(f"Warning: iptables setup may have failed for {server['interface']}")

                threading.Thread(target=self.simulate_server_operation, args=(server_id, 'running')).start()
                return True
            else:
                print(f"Failed to start server {server['name']}")
        except Exception as e:
            print(f"Failed to start server {server_id}: {e}")

        return False

    def stop_server(self, server_id):
        """Stop a WireGuard server using awg-quick with iptables cleanup"""
        server = next((s for s in self.config['servers'] if s['id'] == server_id), None)
        if not server:
            return False

        try:
            # Cleanup iptables rules first
            iptables_cleaned = self.cleanup_iptables(server['interface'], server['subnet'])

            # Use awg-quick to bring down the interface
            result = self.execute_command(f"/usr/bin/awg-quick down {server['interface']}")
            if result is not None:
                server['status'] = 'stopped'
                self.save_config()

                print(f"Server {server['name']} stopped successfully")
                if iptables_cleaned:
                    print(f"iptables rules cleaned up for {server['interface']}")

                threading.Thread(target=self.simulate_server_operation, args=(server_id, 'stopped')).start()
                return True
            else:
                print(f"Failed to stop server {server['name']}")
        except Exception as e:
            print(f"Failed to stop server {server_id}: {e}")

        return False

    def get_server_status(self, server_id):
        """Check actual server status by checking interface"""
        server = next((s for s in self.config['servers'] if s['id'] == server_id), None)
        if not server:
            return "not_found"

        try:
            # Check if interface exists and is up
            result = subprocess.run(["ip", "link", "show", server['interface']], capture_output=True, text=True)
            if "state UNKNOWN" in result.stdout:
                return "running"
            else:
                print(f"Server {server['interface']} currently stopped")
                return "stopped"
        except:
            return "stopped"

    def simulate_server_operation(self, server_id, status):
        """Simulate server operation with status updates"""
        time.sleep(2)
        socketio.emit('server_status', {
            'server_id': server_id,
            'status': status
        })

    def get_client_configs(self, server_id=None):
        """Get all client configs, optionally filtered by server"""
        if server_id:
            # Get from specific server
            server = next((s for s in self.config['servers'] if s['id'] == server_id), None)
            if server:
                return server['clients']
            return []
        else:
            # Get all clients from global dict
            clients = []
            for client_id, client in self.config["clients"].items():
                client_copy = client.copy()
                if 'apply_i_settings' not in client_copy:
                    client_copy['apply_i_settings'] = False
                if 'i_settings' not in client_copy:
                    client_copy['i_settings'] = {}
                clients.append(client_copy)
                if 'status' not in client_copy:
                    client_copy['status'] = 'active'
            return clients

    def get_peer_traffic_for_server(self, server_id):
        server = next((s for s in self.config['servers'] if s['id'] == server_id), None)
        if not server:
            return None

        interface = server['interface']
        try:
            output = self.execute_command(f"/usr/bin/awg show {interface} 2>/dev/null")
            if not output:
                return None
        except Exception as e:
            print(f"Error getting awg show for {interface}: {e}")
            return None

        # Parse output to get traffic and handshake per peer public key
        peer_data = {}

        lines = output.splitlines()
        current_peer = None
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            if line.startswith("peer:"):
                current_peer = line.split("peer:")[1].strip()
                peer_data[current_peer] = {
                    "received": "0 B",
                    "sent": "0 B",
                    "last_handshake": "Never",
                    "endpoint": "",
                    "latest_handshake_epoch": 0
                }
            
            elif line.startswith("transfer:") and current_peer:
                # transfer: 1.39 MiB received, 6.59 MiB sent
                transfer_line = line[len("transfer:"):].strip()
                parts = transfer_line.split(',')
                received = parts[0].strip() if len(parts) > 0 else "0 B"
                sent = parts[1].strip() if len(parts) > 1 else "0 B"
                
                if current_peer in peer_data:
                    peer_data[current_peer]["received"] = received
                    peer_data[current_peer]["sent"] = sent
            
            elif line.startswith("endpoint:") and current_peer:
                endpoint = line.split("endpoint:")[1].strip()
                if current_peer in peer_data:
                    peer_data[current_peer]["endpoint"] = endpoint
            
            elif line.startswith("allowed ips:") and current_peer:
                allowed_ips = line.split("allowed ips:")[1].strip()
                if current_peer in peer_data:
                    peer_data[current_peer]["allowed_ips"] = allowed_ips
            
            elif line.startswith("latest handshake:") and current_peer:
                # latest handshake: 1 minute, 23 seconds ago
                # or: latest handshake: 5 hours, 12 minutes ago
                # or: latest handshake: 2 days, 3 hours ago
                handshake_line = line[len("latest handshake:"):].strip()
                
                if current_peer in peer_data:
                    peer_data[current_peer]["last_handshake"] = handshake_line
                    
                    # Also parse to epoch seconds if available
                    try:
                        # Try to get raw handshake time (might be in different format)
                        if handshake_line != "Never":
                            # Parse relative time to approximate epoch
                            import re
                            import time
                            
                            total_seconds = 0
                            # Parse format like "1 minute, 23 seconds ago"
                            parts = handshake_line.replace(' ago', '').split(', ')
                            for part in parts:
                                match = re.match(r'(\d+)\s+(\w+)', part)
                                if match:
                                    value = int(match.group(1))
                                    unit = match.group(2)
                                    if unit.startswith('second'):
                                        total_seconds += value
                                    elif unit.startswith('minute'):
                                        total_seconds += value * 60
                                    elif unit.startswith('hour'):
                                        total_seconds += value * 3600
                                    elif unit.startswith('day'):
                                        total_seconds += value * 86400
                            
                            peer_data[current_peer]["latest_handshake_epoch"] = time.time() - total_seconds
                    except:
                        peer_data[current_peer]["latest_handshake_epoch"] = 0
            
            i += 1

        # Map data to clients by matching public keys
        clients_data = {}
        for client_id, client in self.config["clients"].items():
            if client.get("server_id") == server_id:
                pubkey = client.get("client_public_key")
                if pubkey in peer_data:
                    clients_data[client_id] = {
                        "received": peer_data[pubkey]["received"],
                        "sent": peer_data[pubkey]["sent"],
                        "last_handshake": peer_data[pubkey]["last_handshake"],
                        "endpoint": peer_data[pubkey]["endpoint"]
                    }
                else:
                    clients_data[client_id] = {
                        "received": "0 B",
                        "sent": "0 B",
                        "last_handshake": "Never",
                        "endpoint": ""
                    }

        return clients_data
    
    def get_server_interface_traffic(self, interface_name):
        """Get RX/TX traffic for a server interface using ifconfig"""
        try:
            result = self.execute_command(f"/sbin/ifconfig {interface_name} 2>/dev/null")
            if not result:
                return None
            
            rx_bytes = "0 B"
            tx_bytes = "0 B"
            
            lines = result.split('\n')
            for line in lines:
                line = line.strip()
                
                if 'RX packets' in line:
                    import re
                # Парсим RX bytes
                match = re.search(r'RX packets:\d+\s+bytes:(\d+)', line)
                if match:
                    bytes_val = int(match.group(1))
                    rx_bytes = self.format_bytes(bytes_val)
                
                # Парсим TX bytes
                match = re.search(r'TX packets:\d+\s+bytes:(\d+)', line)
                if match:
                    bytes_val = int(match.group(1))
                    tx_bytes = self.format_bytes(bytes_val)
            
            return {
                "rx": rx_bytes,
                "tx": tx_bytes
            }
        except Exception as e:
            print(f"Error getting interface traffic for {interface_name}: {e}")
            return None

    def format_bytes(self, bytes_value):
        """Format bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} TB"

    def get_all_servers_traffic(self):
        """Get interface traffic for all servers"""
        servers_traffic = {}
        for server in self.config['servers']:
            interface = server.get('interface')
            if interface:
                traffic = self.get_server_interface_traffic(interface)
                if traffic:
                    servers_traffic[server['id']] = traffic
        return servers_traffic

    def start_traffic_updates(self):
        """Start traffic updates using SocketIO background task"""
        def update_traffic():
            while True:
                try:
                    all_client_traffic = {}
                    for server in self.config['servers']:
                        server_id = server['id']
                        try:
                            traffic = self.get_peer_traffic_for_server(server_id)
                            if traffic:
                                all_client_traffic[server_id] = traffic
                        except Exception as e:
                            print(f"Error getting traffic for server {server_id}: {e}")
                            continue
                    
                    server_interface_traffic = {}
                    for server in self.config['servers']:
                        interface = server.get('interface')
                        if interface:
                            try:
                                traffic = self.get_server_interface_traffic(interface)
                                if traffic:
                                    server_interface_traffic[server['id']] = traffic
                            except Exception as e:
                                print(f"Error getting interface traffic for {interface}: {e}")
                                continue
                    
                    if all_client_traffic or server_interface_traffic:
                        self.socketio.emit('traffic_update', {
                            'timestamp': time.time(),
                            'client_traffic': all_client_traffic,
                            'server_traffic': server_interface_traffic
                        })
                    
                except Exception as e:
                    print(f"Traffic update error: {e}")
                
                time.sleep(self.traffic_update_interval)

        def __init__(self, socketio_instance):
            self.socketio = socketio_instance
            self.config = self.load_config()
            self.ensure_directories()
            self.public_ip = self.detect_public_ip()
            self.traffic_update_interval = 5
            self.suspend_update_interval = 60

            if AUTO_START_SERVERS:
                self.auto_start_servers()
                
            self.start_traffic_updates()
            self.start_suspension_checker()

        def ensure_directories(self):
            os.makedirs(CONFIG_DIR, exist_ok=True)
            os.makedirs(WIREGUARD_CONFIG_DIR, exist_ok=True)
            os.makedirs('/var/log/amnezia', exist_ok=True)

        def detect_public_ip(self):
            try:
                services = ['http://ifconfig.me', 'https://api.ipify.org', 'https://ident.me']
                for service in services:
                    try:
                        response = requests.get(service, timeout=5)
                        if response.status_code == 200:
                            ip = response.text.strip()
                            if self.is_valid_ip(ip):
                                print(f"Detected public IP: {ip}")
                                return ip
                    except:
                        continue
            except Exception as e:
                print(f"Failed to detect public IP: {e}")
            return "YOUR_SERVER_IP"

        def is_valid_ip(self, ip):
            try:
                parts = ip.split('.')
                if len(parts) != 4:
                    return False
                for part in parts:
                    if not 0 <= int(part) <= 255:
                        return False
                return True
            except:
                return False

        def auto_start_servers(self):
            print("Checking for existing servers to auto-start...")
            for server in self.config["servers"]:
                if os.path.exists(server['config_path']):
                    current_status = self.get_server_status(server['id'])
                    if current_status == 'stopped' and server.get('auto_start', True):
                        print(f"Auto-starting server: {server['name']}")
                        self.start_server(server['id'])

        def load_config(self):
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
            return {"servers": [], "clients": {}}

        def save_config(self):
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=2)

        def execute_command(self, command):
            try:
                result = subprocess.run(
                    command, 
                    shell=True, 
                    capture_output=True, 
                    text=True, 
                    check=False,  # Не выбрасываем исключение
                    timeout=5     # Таймаут 5 секунд
                )
                if result.returncode == 0:
                    return result.stdout.strip()
                else:
                    print(f"Command failed with code {result.returncode}: {command}")
                    return None
            except subprocess.TimeoutExpired:
                print(f"Command timeout: {command}")
                return None
            except Exception as e:
                print(f"Command failed: {e}")
                return None