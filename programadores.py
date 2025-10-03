import threading
import time
import random
import os

# --- Constantes e Estado Compartilhado ---

NUM_PROGRAMADORES = 5
MAX_USUARIOS_BD = 2

# Variáveis que representam o estado dos recursos compartilhados
compilador_em_uso = False
usuarios_bd = 0

# Lista para armazenar o estado atual de cada programador
estados = [""] * NUM_PROGRAMADORES

# Primitivas de Sincronização
lock = threading.Lock()
condicao = threading.Condition(lock)


class Programador(threading.Thread):
    """Representa um programador que compete por recursos."""

    def __init__(self, id):
        super().__init__()
        self.id = id

    def _atualizar_estado(self, novo_estado):
        """Atualiza o estado do programador de forma segura."""
        with lock:
            estados[self.id] = novo_estado

    def pensar(self):
        """Simula o programador pensando/descansando."""
        self._atualizar_estado("Pensando")
        time.sleep(random.uniform(3, 6))

    def compilar_ativamente(self):
        """Esta é a fase que usa AMBOS os recursos."""
        self._atualizar_estado("Compilando (usa Compilador+BD)")
        time.sleep(random.uniform(1, 2))

    def resolver_dependencias(self):
        """Nova fase que usa APENAS o banco de dados."""
        self._atualizar_estado("Resolvendo Dependências (usa só BD)")
        time.sleep(random.uniform(2, 4))

    def run(self):
        """O ciclo de vida infinito do programador."""
        global compilador_em_uso, usuarios_bd
        
        while True:
            self.pensar()

            self._atualizar_estado("Esperando por Compilador+BD...")
            
            with condicao:
                while compilador_em_uso or usuarios_bd >= MAX_USUARIOS_BD:
                    condicao.wait()
                compilador_em_uso = True
                usuarios_bd += 1
            
            self.compilar_ativamente()

            with condicao:
                compilador_em_uso = False
                
                # CORREÇÃO DO DEADLOCK:
                # Como já temos o lock, atualizamos o estado diretamente
                # em vez de chamar _atualizar_estado() e tentar pegar o lock de novo.
                estados[self.id] = "Liberou o Compilador"
                
                condicao.notify_all()

            self.resolver_dependencias()

            with condicao:
                usuarios_bd -= 1
                condicao.notify_all()


def exibir_status():
    """Função para limpar a tela e exibir o status atual de todos."""
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print("="*55)
        print("      LABORATÓRIO DE PROGRAMAÇÃO (VERSÃO FINAL)")
        print("="*55)
        
        with lock:
            status_compilador = "OCUPADO" if compilador_em_uso else "LIVRE"
            print(f"Recursos:")
            print(f"  -> Compilador: {status_compilador}")
            print(f"  -> Banco de Dados: {usuarios_bd} de {MAX_USUARIOS_BD} slots ocupados")
            print("-"*55)
            
            print("Programadores:")
            for i in range(NUM_PROGRAMADORES):
                print(f"  -> Programador {i+1}: {estados[i]}")
        
        print("="*55)
        print("(Pressione Ctrl+C para encerrar)")

        time.sleep(0.5)


if __name__ == "__main__":
    # Cria e inicia as threads dos programadores
    programadores = [Programador(i) for i in range(NUM_PROGRAMADORES)]
    for p in programadores:
        p.start()

    # Inicia a função de exibição na thread principal
    try:
        exibir_status()
    except KeyboardInterrupt:
        print("\nEncerrando a simulação.")