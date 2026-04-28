import os
import subprocess
import tempfile
import time
from flask import request, jsonify, send_file, send_from_directory
from flask_login import login_required, current_user

from config import ALLOWED_LOG_TYPES, ALLOWED_LOG_PATHS, resolve_allowed_log_path, format_bytes
from auth import login_attempts

def register_routes(app, amnezia_manager):
    @app.route('/api/system/environment')
    @login_required
    def get_environment():
        """Get environment configuration"""
        return jsonify({
            "auto_start_servers": AUTO_START_SERVERS,
            "default_mtu": DEFAULT_MTU,
            "default_subnet": DEFAULT_SUBNET,
            "default_port": DEFAULT_PORT,
            "default_dns": DEFAULT_DNS,
            "dns_servers": DNS_SERVERS
        })

    @app.route('/api/servers', methods=['POST'])
    @login_required
    def create_server():
        data = request.json
        server = amnezia_manager.create_wireguard_server(data)
        return jsonify(server)

    @app.route('/api/servers/<server_id>', methods=['DELETE'])
    @login_required
    def delete_server(server_id):
        if amnezia_manager.delete_server(server_id):
            return jsonify({"status": "deleted", "server_id": server_id})
        return jsonify({"error": "Server not found"}), 404

    @app.route('/api/servers/<server_id>/start', methods=['POST'])
    @login_required
    def start_server(server_id):
        if amnezia_manager.start_server(server_id):
            return jsonify({"status": "started"})
        return jsonify({"error": "Server not found or failed to start"}), 404

    @app.route('/api/servers/<server_id>/stop', methods=['POST'])
    @login_required
    def stop_server(server_id):
        if amnezia_manager.stop_server(server_id):
            return jsonify({"status": "stopped"})
        return jsonify({"error": "Server not found or failed to stop"}), 404

    @app.route('/api/servers/<server_id>/clients', methods=['GET'])
    @login_required
    def get_server_clients(server_id):
        clients = amnezia_manager.get_client_configs(server_id)
        return jsonify(clients)

    @app.route('/api/servers/<server_id>/clients', methods=['POST'])
    @login_required
    def add_client(server_id):
        data = request.json
        client_name = data.get('name', 'New Client')
        apply_i_settings = data.get('apply_i_settings', False)
        i_settings = data.get('i_settings', {})

        result = amnezia_manager.add_wireguard_client(server_id, client_name, apply_i_settings, i_settings)
        if result:
            client_config, config_content = result
            return jsonify({
                "client": client_config,
                "config": config_content
            })
        return jsonify({"error": "Server not found"}), 404

    @app.route('/api/servers/<server_id>/clients/<client_id>', methods=['DELETE'])
    @login_required
    def delete_client(server_id, client_id):
        if amnezia_manager.delete_client(server_id, client_id):
            return jsonify({"status": "deleted", "client_id": client_id})
        return jsonify({"error": "Client not found"}), 404

    @app.route('/api/servers/<server_id>/clients/<client_id>/i-settings', methods=['PUT'])
    @login_required
    def update_client_i_settings(server_id, client_id):
        data = request.json
        apply_i_settings = data.get('apply_i_settings')
        i_settings = data.get('i_settings', {})
        
        client, config_content = amnezia_manager.update_client_i_settings(
            server_id, client_id, apply_i_settings, i_settings
        )
        
        if client:
            return jsonify({
                "client": client,
                "config": config_content
            })
        return jsonify({"error": "Client not found"}), 404

    @app.route('/api/servers/<server_id>/clients/<client_id>/config')
    @login_required
    def download_client_config(server_id, client_id):
        """Download client configuration file (with comments)"""
        client = amnezia_manager.config["clients"].get(client_id)
        if not client or client.get("server_id") != server_id:
            return jsonify({"error": "Client not found"}), 404

        server = next((s for s in amnezia_manager.config['servers'] if s['id'] == server_id), None)
        if not server:
            return jsonify({"error": "Server not found"}), 404

        # Use full version with comments for download
        config_content = amnezia_manager.generate_wireguard_client_config(
            server, client, include_comments=True
        )

        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write(config_content)
            temp_path = f.name

        filename = f"{client['name']}_{server['name']}.conf"
        return send_file(temp_path, as_attachment=True, download_name=filename)

    @app.route('/api/clients', methods=['GET'])
    @login_required
    def get_all_clients():
        clients = amnezia_manager.get_client_configs()
        return jsonify(clients)

    @app.route('/api/current-user')
    @login_required
    def get_current_user():
        """Get current logged in user info"""
        return jsonify({
            "username": current_user.username,
            "id": current_user.id
        })

    @app.route('/api/system/status')
    @login_required
    def system_status():
        status = {
            "awg_available": os.path.exists("/usr/bin/awg") and os.path.exists("/usr/bin/awg-quick"),
            "public_ip": amnezia_manager.public_ip,
            "total_servers": len(amnezia_manager.config["servers"]),
            "total_clients": len(amnezia_manager.config["clients"]),
            "active_servers": len([s for s in amnezia_manager.config["servers"]
                                if amnezia_manager.get_server_status(s["id"]) == "running"]),
            "timestamp": time.time(),
            "environment": {
                "auto_start_servers": AUTO_START_SERVERS,
                "default_mtu": DEFAULT_MTU,
                "default_subnet": DEFAULT_SUBNET,
                "default_port": DEFAULT_PORT,
                "default_dns": DEFAULT_DNS
            }
        }
        return jsonify(status)

    @app.route('/api/system/refresh-ip')
    @login_required
    def refresh_ip():
        """Refresh public IP address"""
        new_ip = amnezia_manager.detect_public_ip()
        amnezia_manager.public_ip = new_ip

        for server in amnezia_manager.config["servers"]:
            if not server.get('custom_public_ip', False):  # маркер, что IP был задан вручную
                server["public_ip"] = new_ip

        amnezia_manager.save_config()
        return jsonify({"public_ip": new_ip})

    @app.route('/api/servers/<server_id>/config')
    @login_required
    def get_server_config(server_id):
        """Get the raw WireGuard server configuration"""
        server = next((s for s in amnezia_manager.config['servers'] if s['id'] == server_id), None)
        if not server:
            return jsonify({"error": "Server not found"}), 404

        try:
            # Read the actual config file
            if os.path.exists(server['config_path']):
                with open(server['config_path'], 'r') as f:
                    config_content = f.read()

                return jsonify({
                    "server_id": server_id,
                    "server_name": server['name'],
                    "config_path": server['config_path'],
                    "config_content": config_content,
                    "interface": server['interface'],
                    "public_key": server['server_public_key']
                })
            else:
                return jsonify({"error": "Config file not found"}), 404
        except Exception as e:
            return jsonify({"error": f"Failed to read config: {str(e)}"}), 500

    @app.route('/api/servers/<server_id>/config/download')
    @login_required
    def download_server_config(server_id):
        """Download the WireGuard server configuration file"""
        server = next((s for s in amnezia_manager.config['servers'] if s['id'] == server_id), None)
        if not server:
            return jsonify({"error": "Server not found"}), 404

        try:
            if os.path.exists(server['config_path']):
                return send_file(
                    server['config_path'],
                    as_attachment=True,
                    download_name=f"{server['interface']}.conf"
                )
            else:
                return jsonify({"error": "Config file not found"}), 404
        except Exception as e:
            return jsonify({"error": f"Failed to download config: {str(e)}"}), 500

    @app.route('/api/servers/<server_id>/info')
    @login_required
    def get_server_info(server_id):
        """Get detailed server information including config preview and default I values"""
        server = next((s for s in amnezia_manager.config['servers'] if s['id'] == server_id), None)
        if not server:
            return jsonify({"error": "Server not found"}), 404

        # Get current status
        current_status = amnezia_manager.get_server_status(server_id)
        server['current_status'] = current_status

        # Try to read config file for preview
        config_preview = ""
        if os.path.exists(server['config_path']):
            try:
                with open(server['config_path'], 'r') as f:
                    lines = f.readlines()
                    config_preview = ''.join(lines[:min(10, len(lines))])
            except:
                config_preview = "Unable to read config file"

        server_info = {
            "id": server['id'],
            "name": server['name'],
            "protocol": server['protocol'],
            "port": server['port'],
            "status": current_status,
            "interface": server['interface'],
            "config_path": server['config_path'],
            "public_ip": server['public_ip'],
            "server_ip": server['server_ip'],
            "subnet": server['subnet'],
            "mtu": server.get('mtu', 1420),
            "obfuscation_enabled": server['obfuscation_enabled'],
            "obfuscation_params": server.get('obfuscation_params', {}),
            "clients_count": len(server['clients']),
            "created_at": server['created_at'],
            "config_preview": config_preview,
            "public_key": server['server_public_key'],
            "dns": server['dns'],
            "default_i_settings": {
                "i1": DEFAULT_I1,
                "i2": DEFAULT_I2,
                "i3": DEFAULT_I3,
                "i4": DEFAULT_I4,
                "i5": DEFAULT_I5
            }
        }

        return jsonify(server_info)

    @app.route('/api/default-i-settings', methods=['GET'])
    @login_required
    def get_default_i_settings():
        return jsonify({
            "i1": DEFAULT_I1,
            "i2": DEFAULT_I2,
            "i3": DEFAULT_I3,
            "i4": DEFAULT_I4,
            "i5": DEFAULT_I5
        })

    @app.route('/api/servers', methods=['GET'])
    @login_required
    def get_servers():
        # Update server status based on actual interface state
        for server in amnezia_manager.config["servers"]:
            server["status"] = amnezia_manager.get_server_status(server["id"])
            # Ensure MTU is included in basic server list
            if 'mtu' not in server:
                server['mtu'] = 1420  # Default value

        amnezia_manager.save_config()
        return jsonify(amnezia_manager.config["servers"])

    @app.route('/api/system/iptables-test')
    @login_required
    def iptables_test():
        """Test iptables setup for a specific server"""
        server_id = request.args.get('server_id')
        if not server_id:
            return jsonify({"error": "server_id parameter required"}), 400

        server = next((s for s in amnezia_manager.config['servers'] if s['id'] == server_id), None)
        if not server:
            return jsonify({"error": "Server not found"}), 404

        # Test iptables rules
        try:
            # Check if rules exist
            check_commands = [
                f"iptables -L INPUT -n | grep {server['interface']}",
                f"iptables -L FORWARD -n | grep {server['interface']}",
                f"iptables -t nat -L POSTROUTING -n | grep {server['subnet']}"
            ]

            results = {}
            for cmd in check_commands:
                try:
                    result = amnezia_manager.execute_command(cmd)
                    results[cmd] = "Found" if result else "Not found"
                except:
                    results[cmd] = "Error"

            return jsonify({
                "server_id": server_id,
                "server_name": server['name'],
                "interface": server['interface'],
                "subnet": server['subnet'],
                "iptables_check": results
            })

        except Exception as e:
            return jsonify({"error": f"iptables test failed: {str(e)}"}), 500
        
    @app.route('/api/servers/<server_id>/clients/<client_id>/config-both')
    @login_required
    def get_client_config_both(server_id, client_id):
        """Get both clean and full client configurations"""
        client = amnezia_manager.config["clients"].get(client_id)
        if not client or client.get("server_id") != server_id:
            return jsonify({"error": "Client not found"}), 404

        server = next((s for s in amnezia_manager.config['servers'] if s['id'] == server_id), None)
        if not server:
            return jsonify({"error": "Server not found"}), 404

        # Generate both versions
        clean_config = amnezia_manager.generate_wireguard_client_config(
            server, client, include_comments=False
        )
        
        full_config = amnezia_manager.generate_wireguard_client_config(
            server, client, include_comments=True
        )
        
        return jsonify({
            "server_id": server_id,
            "client_id": client_id,
            "client_name": client['name'],
            "clean_config": clean_config,
            "full_config": full_config,
            "clean_length": len(clean_config),
            "full_length": len(full_config),
            "created_at": client['created_at'],
            "created_at_readable": time.ctime(client.get('created_at')) if client.get('created_at') else None,
            "suspend_at": client.get('suspend_at'),
            "suspend_at_readable": time.ctime(client.get('suspend_at')) if client.get('suspend_at') else None
        })
        
    @app.route('/api/servers/<server_id>/clients/<client_id>/suspend', methods=['POST'])
    @login_required
    def suspend_client(server_id, client_id):
        """Suspend a client"""
        success, message = amnezia_manager.suspend_client(server_id, client_id)
        if success:
            return jsonify({"status": "suspended", "client_id": client_id, "message": message})
        return jsonify({"error": message}), 404

    @app.route('/api/servers/<server_id>/clients/<client_id>/activate', methods=['POST'])
    @login_required
    def activate_client(server_id, client_id):
        """Activate a suspended client"""
        success, message = amnezia_manager.activate_client(server_id, client_id)
        if success:
            return jsonify({"status": "activated", "client_id": client_id, "message": message})
        return jsonify({"error": message}), 404

    @app.route('/api/servers/<server_id>/clients/<client_id>/suspend-time', methods=['PUT'])
    @login_required
    def update_client_suspend_time(server_id, client_id):
        """Update client scheduled suspension time"""
        data = request.json
        suspend_at = data.get('suspend_at')
        
        # Convert ISO datetime string to timestamp if provided
        if suspend_at:
            from datetime import datetime
            try:
                dt = datetime.fromisoformat(suspend_at.replace('Z', '+00:00'))
                suspend_at = dt.timestamp()
            except:
                return jsonify({"error": "Invalid datetime format"}), 400
        
        client, message = amnezia_manager.update_client_suspend_time(server_id, client_id, suspend_at)
        if client:
            return jsonify({
                "client": client,
                "message": message
            })
        return jsonify({"error": message}), 404
        
    @app.route('/api/servers/<server_id>/traffic')
    @login_required
    def get_server_traffic(server_id):
        traffic = amnezia_manager.get_peer_traffic_for_server(server_id)
        if traffic is None:
            return jsonify({"error": "Server not found or no traffic data"}), 404
        return jsonify(traffic)

    @app.route('/api/servers/traffic')
    @login_required
    def get_all_servers_traffic():
        """Get interface traffic for all servers"""
        traffic = amnezia_manager.get_all_servers_traffic()
        return jsonify(traffic)

    @app.route('/api/logs/list')
    @login_required
    def get_logs_list():
        """Get list of available log files"""
        # Check which files exist
        available_logs = []
        for log in ALLOWED_LOG_FILES:
            if os.path.exists(log["path"]):
                stat = os.stat(log["path"])
                available_logs.append({
                    "name": log["name"],
                    "path": log["path"],
                    "type": log["type"],
                    "size": stat.st_size,
                    "size_human": format_bytes(stat.st_size)
                })
        
        return jsonify(available_logs)

    @app.route('/api/logs/view')
    @login_required
    def view_log():
        """Get last N lines of a log file"""
        requested_path = request.args.get('path')
        requested_type = request.args.get('type')
        lines = request.args.get('lines', 100, type=int)

        log_path = None
        if requested_type and requested_type in ALLOWED_LOG_TYPES:
            log_path = ALLOWED_LOG_TYPES[requested_type]
        elif requested_path and requested_path in ALLOWED_LOG_PATHS:
            log_path = requested_path

        if not log_path:
            return jsonify({"error": "Invalid log selection"}), 400
        
        if not os.path.exists(log_path):
            return jsonify({"error": "Log file not found"}), 404
        
        try:
            # Use tail command to get last N lines
            result = subprocess.run(
                ["tail", "-n", str(lines), log_path],
                capture_output=True,
                text=True,
                check=True
            )
            
            return jsonify({
                "path": log_path,
                "lines": result.stdout,
                "line_count": len(result.stdout.splitlines()),
                "total_lines": int(subprocess.run(
                    ["wc", "-l", log_path],
                    capture_output=True,
                    text=True,
                    check=True
                ).stdout.split()[0])
            })
        except subprocess.CalledProcessError as e:
            return jsonify({"error": f"Failed to read log: {str(e)}"}), 500

    @app.route('/api/logs/download')
    @login_required
    def download_log():
        """Download complete log file"""
        requested_type = request.args.get('type')

        log_path = None
        if requested_type and requested_type in ALLOWED_LOG_TYPES:
            log_path = ALLOWED_LOG_TYPES[requested_type]

        safe_log_path = resolve_allowed_log_path(log_path)
        if not safe_log_path:
            return jsonify({"error": "Invalid log selection"}), 400
        
        if not os.path.exists(safe_log_path):
            return jsonify({"error": "Log file not found"}), 404
        
        # Get filename from path
        filename = os.path.basename(safe_log_path)
        safe_log_dir = os.path.dirname(safe_log_path)
        
        return send_from_directory(
            directory=safe_log_dir,
            path=filename,
            as_attachment=True,
            download_name=f"{filename}",
            mimetype="text/plain"
        )