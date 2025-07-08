import threading

class LamportClock:
    """Implementação do Relógio Lógico de Lamport"""
    
    def __init__(self):
        self.time = 0
        self.lock = threading.Lock()
    
    def tick(self):
        """Incrementa o relógio local"""
        with self.lock:
            self.time += 1
            return self.time
    
    def update(self, received_time):
        """Atualiza o relógio com base em mensagem recebida"""
        with self.lock:
            self.time = max(self.time, received_time) + 1
            return self.time
    
    def get_time(self):
        """Retorna o tempo atual do relógio"""
        with self.lock:
            return self.time