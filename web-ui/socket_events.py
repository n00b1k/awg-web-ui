import time
from flask_socketio import SocketIO
from flask_login import current_user

def register_socket_events(socketio, amnezia_manager):
    @socketio.on('connect')
    def handle_connect():
        if not current_user.is_authenticated:
            return False
        print(f"WebSocket connected")
        
        socketio.emit('status', {
            'message': 'Connected to AmneziaWG Web UI',
            'public_ip': amnezia_manager.public_ip
        })
        
        all_client_traffic = {}
        for server in amnezia_manager.config['servers']:
            server_id = server['id']
            traffic = amnezia_manager.get_peer_traffic_for_server(server_id)
            if traffic:
                all_client_traffic[server_id] = traffic
        
        if all_client_traffic:
            socketio.emit('traffic_update', {
                'timestamp': time.time(),
                'client_traffic': all_client_traffic
            })

    @socketio.on('disconnect')
    def handle_disconnect():
        print(f"WebSocket disconnected")