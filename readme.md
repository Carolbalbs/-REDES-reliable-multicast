# Reliable Multicast com Relógio de Lamport

## Visão Geral

Este projeto implementa um sistema de comunicação distribuída que combina:
- **Reliable Multicast**: Garantia de entrega confiável de mensagens para todos os processos
- **Relógio de Lamport**: Ordenação lógica de eventos em sistemas distribuídos assíncronos

## Arquitetura do Sistema

### Componentes Principais

1. **LamportClock**: Implementa o relógio lógico de Lamport
2. **ReliableMulticast**: Classe principal que gerencia a comunicação entre processos
3. **Sistema de ACK**: Mecanismo de confirmação para garantir entrega confiável
4. **Buffer de Mensagens**: Controle de duplicatas e reordenação

### Protocolo de Comunicação

#### 1. Envio de Mensagem
```
Processo A                           Processos B, C, D
    |                                        |
    |-- Increment Lamport Clock              |
    |-- Create Message with Timestamp        |
    |-- Send to All Peers ------------------>|
    |-- Deliver Locally                      |-- Receive Message
    |-- Wait for ACKs                        |-- Update Lamport Clock
    |                                        |-- Send ACK
    |<-- Receive ACKs -----------------------|-- Deliver Message
    |-- Mark as Confirmed                    |
```

#### 2. Estrutura das Mensagens

**Mensagem Multicast:**
```json
{
    "type": "MULTICAST",
    "id": "P1_1",
    "sender": "P1",
    "content": "Hello World",
    "lamport_time": 5,
    "timestamp": "2025-06-28T10:30:45.123"
}
```

**Mensagem de ACK:**
```json
{
    "type": "ACK",
    "msg_id": "P1_1",
    "sender": "P2",
    "lamport_time": 6
}
```

## Características Implementadas

### Reliable Multicast
- ✅ **Entrega Garantida**: Mensagens são reenviadas até confirmação
- ✅ **Detecção de Duplicatas**: Evita entrega múltipla da mesma mensagem
- ✅ **Timeout e Retry**: Reenvio automático de mensagens não confirmadas
- ✅ **Controle de Sequência**: Numeração única para cada mensagem

### Relógio de Lamport
- ✅ **Sincronização de Eventos**: Ordenação causal de eventos
- ✅ **Atualização Automática**: Clock atualizado a cada envio/recebimento
- ✅ **Thread Safety**: Operações atômicas no relógio lógico
- ✅ **Visualização**: Timestamps visíveis em todos os logs

### Funcionalidades Adicionais
- ✅ **Interface Interativa**: Comandos para envio de mensagens
- ✅ **Estatísticas**: Contadores de mensagens enviadas/recebidas
- ✅ **Logs Detalhados**: Registro completo de eventos
- ✅ **Recuperação de Falhas**: Reconexão automática em caso de erro

## Como Executar

### Pré-requisitos
- Python 3.6 ou superior
- Sistema operacional Unix/Linux/macOS (ou Windows com WSL)

### Instalação
```bash
# Salve o código em reliable_multicast.py
chmod +x reliable_multicast.py
chmod +x test_script.sh
```

### Execução Manual

**Terminal 1 (Processo P1):**
```bash
python3 reliable_multicast.py P1 8001 8002 8003
```

**Terminal 2 (Processo P2):**
```bash
python3 reliable_multicast.py P2 8002 8001 8003
```

**Terminal 3 (Processo P3):**
```bash
python3 reliable_multicast.py P3 8003 8001 8002
```

### Execução com Script de Teste

**Demonstração Automática:**
```bash
./test_script.sh demo
```

**Modo Interativo:**
```bash
./test_script.sh interactive
```

## Comandos Disponíveis

Uma vez que o processo esteja executando, você pode usar:

- `send <mensagem>` - Envia mensagem multicast
- `stats` - Mostra estatísticas do processo
- `help` - Lista comandos disponíveis
- `quit` - Finaliza o processo

### Exemplo de Uso
```
P1> send Hello from P1
P1> send This is a test message
P1> stats
P1> quit
```

## Exemplo de Saída

```
[10:30:45.123] [Lamport:   1] [SISTEMA     ] Processo P1 iniciado na porta 8001
[10:30:45.124] [Lamport:   1] [CONEXAO     ] Conectado ao peer localhost:8002
[10:30:45.125] [Lamport:   1] [CONEXAO     ] Conectado ao peer localhost:8003
[10:30:50.100] [Lamport:   2] [ENVIO       ] Mensagem 'Hello World' enviada (Lamport: 2)
[10:30:50.101] [Lamport:   4] [RECEBIMENTO ] Mensagem de P2: 'Hi there' (Lamport: 3 -> 4)
[10:30:50.102] [Lamport:   4] [CONFIRMACAO ] Mensagem P1_1 confirmada por todos
```

## Análise do Relógio de Lamport

### Comportamento Observado

1. **Incremento Local**: Toda operação local incrementa o relógio
2. **Sincronização**: Ao receber mensagem, o relógio é atualizado para max(local, recebido) + 1
3. **Ordenação Causal**: Eventos podem ser ordenados pelos timestamps de Lamport
4. **Concorrência**: Eventos com mesmo timestamp são concorrentes

### Exemplo de Evolução do Relógio

```
P1: [1] -> [2] send msg -> [3] recv ack -> [4]
P2: [1] -> [3] recv msg -> [4] send ack -> [5]
P3: [1] -> [5] recv msg -> [6] send ack -> [7]
```

## Tolerância a Falhas

### Características Implementadas

1. **Timeout e Retry**: Mensagens não confirmadas são reenviadas
2. **Reconexão**: Tentativas automáticas de reconexão
3. **Buffer de Mensagens**: Armazenamento temporário para garantir entrega
4. **Detecção de Falhas**: Logs de erros de comunicação

### Limitações

- Não implementa detecção de falhas bizantinas
- Assume que processos eventuaalmente se recuperam
- Não implementa consensus para ordenação total

## Métricas e Estatísticas

O sistema coleta as seguintes métricas:

- `messages_sent`: Total de mensagens enviadas
- `messages_received`: Total de mensagens recebidas
- `messages_delivered`: Total de mensagens entregues à aplicação
- `acks_sent`: Total de confirmações enviadas
- `acks_received`: Total de confirmações recebidas
- `lamport_time`: Tempo atual do relógio de Lamport
- `pending_messages`: Mensagens aguardando confirmação
- `delivered_messages`: Total de mensagens únicas entregues

## Testes Sugeridos

### Teste 1: Comunicação Básica
1. Inicie 3 processos
2. Envie mensagens de cada processo
3. Verifique se todas as mensagens são entregues
4. Observe a evolução dos timestamps de Lamport

### Teste 2: Concorrência
1. Envie mensagens simultaneamente de múltiplos processos
2. Observe como os relógios se sincronizam
3. Analise a ordenação causal dos eventos

### Teste 3: Recuperação de Falhas
1. Inicie os processos
2. Finalize um processo durante comunicação
3. Reinicie o processo
4. Verifique se mensagens são reenviadas

### Teste 4: Carga de Trabalho
1. Envie múltiplas mensagens rapidamente
2. Monitore as estatísticas
3. Verifique se todas as mensagens são confirmadas

## Extensões Possíveis

1. **Ordenação Total**: Implementar algoritmo de ordenação total
2. **Persistência**: Salvar estado em disco para recuperação
3. **Interface Gráfica**: Visualização em tempo real dos eventos
4. **Balanceamento**: Distribuição de carga entre processos
5. **Segurança**: Autenticação e criptografia das mensagens
6. **Detecção de Falhas**: Algoritmos de failure detection
7. **Consenso**: Implementação de algoritmos como Raft ou PBFT

## Conclusão

Este projeto demonstra com sucesso a implementação de um sistema distribuído que combina comunicação confiável com ordenação lógica de eventos. O uso do Relógio de Lamport permite compreender a causalidade entre eventos, enquanto o Reliable Multicast garante que todas as mensagens sejam entregues de forma consistente.

A implementação serve como base sólida para estudos mais avançados em sistemas distribuídos e pode ser estendida com funcionalidades adicionais conforme necessário.