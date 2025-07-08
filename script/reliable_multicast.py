import sys
import time
from multicast import ReliableMulticast


def main():
    """Função principal"""
    if len(sys.argv) < 3:
        print("Uso: python main.py <process_id> <port> [peer_ports...]")
        print("Exemplo: python main.py P1 8001 8002 8003")
        sys.exit(1)
    
    process_id = sys.argv[1]
    port = int(sys.argv[2])
    peer_ports = [int(p) for p in sys.argv[3:]]
    
    # Cria lista de peers
    peers = [('localhost', p) for p in peer_ports]
    
    # Cria e inicia processo
    process = ReliableMulticast(process_id, port, peers)
    process.start()
    
    print(f"\n=== Processo {process_id} iniciado ===")
    print("Comandos disponíveis:")
    print("  send <mensagem>  - Envia mensagem multicast")
    print("  stats           - Mostra estatísticas")
    print("  quit            - Finaliza processo")
    print("=" * 50)
    
    try:
        # Aguarda um pouco para conexões se estabelecerem
        time.sleep(2)
        
        # Interface de comando
        while True:
            try:
                command = input(f"{process_id}> ").strip()
                
                if command.startswith("send "):
                    message = command[5:]
                    process.multicast_send(message)
                
                elif command == "stats":
                    stats = process.get_stats()
                    print("\n=== Estatísticas ===")
                    for key, value in stats.items():
                        print(f"{key}: {value}")
                    print("=" * 20)
                
                elif command == "quit":
                    break
                
                elif command == "help":
                    print("Comandos: send <msg>, stats, quit, help")
                
                else:
                    print("Comando inválido. Digite 'help' para ajuda.")
                    
            except KeyboardInterrupt:
                break
                
    except KeyboardInterrupt:
        pass
    finally:
        process.stop()

if __name__ == "__main__":
    main()