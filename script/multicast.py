import socket
import threading
import json
import time
import random
from datetime import datetime
from collections import defaultdict
import queue
from lamport import LamportClock

class ReliableMulticast:
    """Implementação do Reliable Multicast"""
    
    def __init__(self, process_id, port, peers):
        self.process_id = process_id
        self.port = port
        self.peers = peers  # Lista de (host, port) dos outros processos
        self.clock = LamportClock()
        
        # Controle de mensagens
        self.message_buffer = {}  # Buffer para mensagens fora de ordem
        self.delivered_messages = set()  # IDs de mensagens já entregues
        self.ack_received = defaultdict(set)  # ACKs recebidos por mensagem
        self.pending_messages = {}  # Mensagens aguardando ACKs
        
        # Controle de sequência
        self.sequence_number = 0
        self.sequence_lock = threading.Lock()
        
        # Sockets e threads
        self.server_socket = None
        self.client_sockets = {}
        self.running = False
        
        # Fila de eventos para visualização
        self.event_queue = queue.Queue()
        
        # Estatísticas
        self.stats = {
            'messages_sent': 0,
            'messages_received': 0,
            'messages_delivered': 0,
            'acks_sent': 0,
            'acks_received': 0
        }
    
    def get_next_sequence(self):
        """Gera próximo número de sequência"""
        with self.sequence_lock:
            self.sequence_number += 1
            return self.sequence_number
    
    def start(self):
        """Inicia o processo"""
        self.running = True
        
        # Inicia servidor para receber mensagens
        self.start_server()
        
        # Conecta aos peers
        self.connect_to_peers()
        
        # Inicia thread para processar eventos
        self.event_thread = threading.Thread(target=self.process_events)
        self.event_thread.daemon = True
        self.event_thread.start()
        
        # Inicia thread para reenvio de mensagens não confirmadas
        self.retry_thread = threading.Thread(target=self.retry_unacknowledged)
        self.retry_thread.daemon = True
        self.retry_thread.start()
        
        self.log_event("SISTEMA", f"Processo {self.process_id} iniciado na porta {self.port}")
    
    def start_server(self):
        """Inicia servidor para receber mensagens"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('localhost', self.port))
        self.server_socket.listen(10)
        
        # Thread para aceitar conexões
        self.server_thread = threading.Thread(target=self.accept_connections)
        self.server_thread.daemon = True
        self.server_thread.start()
    
    def accept_connections(self):
        """Aceita conexões de outros processos"""
        while self.running:
            try:
                client_socket, address = self.server_socket.accept()
                # Thread para lidar com cada cliente
                client_thread = threading.Thread(
                    target=self.handle_client, 
                    args=(client_socket, address)
                )
                client_thread.daemon = True
                client_thread.start()
            except:
                break
    
    def handle_client(self, client_socket, address):
        """Lida com mensagens de um cliente específico"""
        try:
            while self.running:
                data = client_socket.recv(4096)
                if not data:
                    break
                
                try:
                    message = json.loads(data.decode())
                    self.handle_received_message(message)
                except json.JSONDecodeError:
                    self.log_event("ERRO", f"Mensagem malformada de {address}")
                    
        except:
            pass
        finally:
            client_socket.close()
    
    def connect_to_peers(self):
        """Conecta aos outros processos"""
        for peer_host, peer_port in self.peers:
            max_retries = 3
            retry_delay = 1
            
            for attempt in range(max_retries):
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(5)  # Timeout de 5 segundos
                    sock.connect((peer_host, peer_port))
                    self.client_sockets[(peer_host, peer_port)] = sock
                    self.log_event("CONEXAO", f"Conectado ao peer {peer_host}:{peer_port}")
                    break
                except Exception as e:
                    if attempt < max_retries - 1:
                        self.log_event("AVISO", f"Tentativa {attempt + 1} falhou para {peer_host}:{peer_port}, tentando novamente...")
                        time.sleep(retry_delay)
                    else:
                        self.log_event("ERRO", f"Falha ao conectar com {peer_host}:{peer_port}: {e}")
                        # Continua sem este peer por enquanto
    
    def multicast_send(self, content):
        """Envia mensagem multicast confiável"""
        # Incrementa relógio de Lamport
        lamport_time = self.clock.tick()
        
        # Cria mensagem
        message = {
            'type': 'MULTICAST',
            'id': f"{self.process_id}_{self.get_next_sequence()}",
            'sender': self.process_id,
            'content': content,
            'lamport_time': lamport_time,
            'timestamp': datetime.now().isoformat()
        }
        
        # Armazena mensagem para possível reenvio
        self.pending_messages[message['id']] = {
            'message': message,
            'acks_needed': len(self.peers),
            'sent_time': time.time()
        }
        
        # Envia para todos os peers
        self.broadcast_message(message)
        
        # Entrega localmente
        self.deliver_message(message)
        
        self.stats['messages_sent'] += 1
        self.log_event("ENVIO", f"Mensagem '{content}' enviada (Lamport: {lamport_time})")
    
    def broadcast_message(self, message):
        """Envia mensagem para todos os peers"""
        message_data = json.dumps(message).encode()
        
        for peer, sock in self.client_sockets.items():
            try:
                sock.send(message_data)
            except Exception as e:
                self.log_event("ERRO", f"Falha ao enviar para {peer}: {e}")
    
    def handle_received_message(self, message):
        """Processa mensagem recebida"""
        msg_type = message.get('type')
        
        if msg_type == 'MULTICAST':
            self.handle_multicast_message(message)
        elif msg_type == 'ACK':
            self.handle_ack_message(message)
    
    def handle_multicast_message(self, message):
        """Processa mensagem multicast recebida"""
        msg_id = message['id']
        sender = message['sender']
        lamport_time = message['lamport_time']
        
        # Atualiza relógio de Lamport
        self.clock.update(lamport_time)
        
        # Evita duplicatas
        if msg_id in self.delivered_messages:
            return
        
        # Envia ACK
        self.send_ack(sender, msg_id)
        
        # Entrega mensagem
        self.deliver_message(message)
        
        self.stats['messages_received'] += 1
        self.log_event("RECEBIMENTO", 
                      f"Mensagem de {sender}: '{message['content']}' "
                      f"(Lamport: {lamport_time} -> {self.clock.get_time()})")
    
    def send_ack(self, sender, msg_id):
        """Envia ACK para o remetente"""
        ack_message = {
            'type': 'ACK',
            'msg_id': msg_id,
            'sender': self.process_id,
            'lamport_time': self.clock.tick()
        }
        
        # Envia ACK para todos os peers (broadcast)
        # Cada peer filtrará se o ACK é para ele
        ack_data = json.dumps(ack_message).encode()
        for peer, sock in self.client_sockets.items():
            try:
                sock.send(ack_data)
                self.stats['acks_sent'] += 1
            except Exception as e:
                self.log_event("ERRO", f"Falha ao enviar ACK para {peer}: {e}")
    
    def handle_ack_message(self, ack):
        """Processa ACK recebido"""
        msg_id = ack['msg_id']
        sender = ack['sender']
        
        # Atualiza relógio
        self.clock.update(ack['lamport_time'])
        
        # Verifica se o ACK é para uma mensagem nossa
        if msg_id in self.pending_messages:
            # Registra ACK
            self.ack_received[msg_id].add(sender)
            
            # Verifica se recebeu todos os ACKs necessários
            acks_needed = self.pending_messages[msg_id]['acks_needed']
            acks_received = len(self.ack_received[msg_id])
            
            if acks_received >= acks_needed:
                # Mensagem confirmada por todos
                del self.pending_messages[msg_id]
                self.log_event("CONFIRMACAO", f"Mensagem {msg_id} confirmada por todos ({acks_received}/{acks_needed})")
            else:
                self.log_event("ACK_RECEBIDO", f"ACK de {sender} para {msg_id} ({acks_received}/{acks_needed})")
        
        self.stats['acks_received'] += 1
    
    def deliver_message(self, message):
        """Entrega mensagem à aplicação"""
        msg_id = message['id']
        
        if msg_id not in self.delivered_messages:
            self.delivered_messages.add(msg_id)
            self.stats['messages_delivered'] += 1
            
            # Adiciona à fila de eventos
            self.event_queue.put({
                'type': 'DELIVERY',
                'message': message,
                'local_time': self.clock.get_time()
            })
    
    def retry_unacknowledged(self):
        """Reenvia mensagens não confirmadas"""
        while self.running:
            time.sleep(5)  # Verifica a cada 5 segundos
            
            current_time = time.time()
            for msg_id, msg_info in list(self.pending_messages.items()):
                # Reenvia se passou mais de 10 segundos
                if current_time - msg_info['sent_time'] > 10:
                    self.broadcast_message(msg_info['message'])
                    msg_info['sent_time'] = current_time
                    self.log_event("REENVIO", f"Reenviando mensagem {msg_id}")
    
    def process_events(self):
        """Processa eventos para visualização"""
        while self.running:
            try:
                event = self.event_queue.get(timeout=1)
                # Aqui você pode processar eventos especiais
                # Por exemplo, ordenação por Lamport timestamp
            except queue.Empty:
                continue
    
    def log_event(self, event_type, message):
        """Registra evento com timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        lamport_time = self.clock.get_time()
        
        log_message = f"[{timestamp}] [Lamport: {lamport_time:3d}] [{event_type:12s}] {message}"
        print(log_message)
    
    def get_stats(self):
        """Retorna estatísticas do processo"""
        return {
            **self.stats,
            'lamport_time': self.clock.get_time(),
            'pending_messages': len(self.pending_messages),
            'delivered_messages': len(self.delivered_messages)
        }
    
    def stop(self):
        """Para o processo"""
        self.running = False
        
        # Fecha sockets
        if self.server_socket:
            self.server_socket.close()
        
        for sock in self.client_sockets.values():
            sock.close()
        
        self.log_event("SISTEMA", f"Processo {self.process_id} finalizado")
