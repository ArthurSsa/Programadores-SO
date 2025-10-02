import threading
import time
import random
import os

# --- Constantes e Estado Compartilhado ---
NUM_PROGRAMMERS = 5
MAX_DB_USERS = 2

# Variáveis de estado para os recursos
compiler_in_use = False
db_users = 0

# Lista para armazenar o status de cada programador para exibição
programmers_status = ["Iniciando..." for _ in range(NUM_PROGRAMMERS)]

# Primitiva de sincronização: Condition é ideal para gerenciar o acesso
# a múltiplos recursos e evitar deadlock.
# Ela agrupa um Lock com métodos wait() e notify().
resource_condition = threading.Condition()

def clear_screen():
    """Limpa o terminal para uma exibição mais limpa."""
    os.system('cls' if os.name == 'nt' else 'clear')

def programmer_life(prog_id):
    """O ciclo de vida de um programador."""
    global compiler_in_use, db_users, programmers_status

    while True:
        # --- Fase 1: Pensar ---
        programmers_status[prog_id] = "Pensando (descansando)"
        time.sleep(random.uniform(3, 7)) # Pensa por um tempo aleatório

        # --- Fase 2: Tentar adquirir recursos ---
        programmers_status[prog_id] = "Aguardando recursos"
        
        with resource_condition:
            # Espera em um loop até que AMBAS as condições sejam verdadeiras:
            # 1. O compilador esteja livre.
            # 2. Haja um slot livre no banco de dados.
            # O método wait() libera o lock interno e espera por uma notificação.
            # Quando acordado, ele re-adquire o lock e verifica a condição novamente.
            while compiler_in_use or db_users >= MAX_DB_USERS:
                resource_condition.wait()

            # --- Recursos adquiridos ---
            # Marca os recursos como em uso
            compiler_in_use = True
            db_users += 1
            programmers_status[prog_id] = f"COMPILANDO (BD em uso: {db_users}/2)"

        # --- Fase 3: Compilar ---
        # A compilação ocorre fora do bloco 'with' para permitir que outros
        # threads (o loop de exibição, por exemplo) possam rodar.
        time.sleep(random.uniform(2, 5)) # Simula o tempo de compilação

        # --- Fase 4: Liberar recursos ---
        with resource_condition:
            programmers_status[prog_id] = "Liberando recursos"
            compiler_in_use = False
            db_users -= 1
            
            # Notifica TODAS as outras threads que estão esperando para que elas
            # possam verificar se as condições agora são favoráveis.
            resource_condition.notify_all()


def display_status():
    """Função para exibir o estado do sistema continuamente."""
    while True:
        clear_screen()
        print("--- Laboratório de Programação ---")
        print("-" * 32)
        
        # Acessa os dados de forma segura para evitar condições de corrida na leitura
        with resource_condition:
            for i in range(NUM_PROGRAMMERS):
                print(f"Programador {i+1}: {programmers_status[i]}")
            
            print("-" * 32)
            print("Estado dos Recursos:")
            compiler_status = "OCUPADO" if compiler_in_use else "LIVRE"
            print(f"  Compilador: {compiler_status}")
            print(f"  Banco de Dados: {db_users} de {MAX_DB_USERS} conexões em uso")
            print("-" * 32)
        
        time.sleep(0.5) # Atualiza a tela a cada meio segundo

if __name__ == "__main__":
    # Cria e inicia as threads dos programadores
    threads = []
    for i in range(NUM_PROGRAMMERS):
        thread = threading.Thread(target=programmer_life, args=(i,))
        thread.daemon = True  # Permite que o programa principal feche mesmo com threads rodando
        threads.append(thread)

    for thread in threads:
        thread.start()

    # Inicia a função de exibição no thread principal
    try:
        display_status()
    except KeyboardInterrupt:
        print("\nEncerrando a simulação.")