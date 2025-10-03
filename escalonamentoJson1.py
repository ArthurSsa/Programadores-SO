import json
from typing import List, Dict, Tuple
from dataclasses import dataclass

@dataclass
class Process:
    pid: str
    arrival_time: int
    burst_time: int
    remaining_time: int = 0
    first_response: int = -1
    
    def __post_init__(self):
        self.remaining_time = self.burst_time

class SchedulingSimulator:
    def __init__(self, config: dict):
        self.config = config
        # CORREÇÃO: Acessar 'context_switch_cost' dentro de 'metadata'
        self.context_switch_cost = config.get('metadata', {}).get('context_switch_cost', 1)
        self.processes = [
            Process(
                pid=p['pid'],
                arrival_time=p['arrival_time'],
                burst_time=p['burst_time']
            )
            for p in config['workload']['processes']
        ]

    # =================================================================================
    # NOVO MÉTODO ADICIONADO PARA CALCULAR A VAZÃO CORRETAMENTE
    # =================================================================================
    def _calculate_throughput(self, timeline: List[Dict]) -> float:
        """Calcula a vazão com base em uma janela de tempo definida no config."""
        T = self.config['metadata'].get('throughput_window_T')
        
        # Se a janela não for definida, retorna 0 ou outra métrica de fallback.
        if not T:
            return 0

        # Encontra o tempo de conclusão final para cada processo (importante para RR)
        completion_times = {}
        for entry in timeline:
            pid = entry['pid']
            completion_times[pid] = max(completion_times.get(pid, 0), entry['end'])
            
        # Conta quantos processos terminaram dentro da janela T
        processes_completed_in_window = sum(
            1 for pid, end_time in completion_times.items() if end_time <= T
        )
        
        # Evita divisão por zero
        if T == 0:
            return 0
        
        # Vazão = Processos Concluídos / Janela de Tempo
        return processes_completed_in_window / T
        
    def simulate_fcfs(self) -> Dict:
        """First Come, First Served"""
        processes = sorted(self.processes, key=lambda p: p.arrival_time)
        
        current_time = 0
        total_wait = 0
        total_turnaround = 0
        total_response = 0
        context_switches = 0
        timeline = []
        
        for idx, proc in enumerate(processes):
            if current_time < proc.arrival_time:
                current_time = proc.arrival_time
            
            response_time = current_time - proc.arrival_time
            total_response += response_time
            
            if idx > 0:
                current_time += self.context_switch_cost
                context_switches += 1
            
            timeline.append({
                'pid': proc.pid,
                'start': current_time,
                'end': current_time + proc.burst_time
            })
            current_time += proc.burst_time
            
            turnaround_time = current_time - proc.arrival_time
            wait_time = turnaround_time - proc.burst_time
            
            total_wait += wait_time
            total_turnaround += turnaround_time
        
        n = len(processes)
        # CORREÇÃO: Chamar a função para calcular a vazão
        throughput = self._calculate_throughput(timeline)

        return {
            'algorithm': 'FCFS',
            'quantum': '-',
            'avg_wait_time': total_wait / n,
            'avg_turnaround_time': total_turnaround / n,
            'avg_response_time': total_response / n,
            'throughput': throughput, # CORREÇÃO: Usar o valor calculado
            'context_switches': context_switches,
            'timeline': timeline
        }
    
    def simulate_sjf(self) -> Dict:
        """Shortest Job First (não-preemptivo)"""
        processes = [Process(p.pid, p.arrival_time, p.burst_time) 
                    for p in self.processes]
        
        current_time = 0
        total_wait = 0
        total_turnaround = 0
        total_response = 0
        context_switches = 0
        timeline = []
        completed = set()
        
        while len(completed) < len(processes):
            available = [p for p in processes 
                        if p.arrival_time <= current_time and p.pid not in completed]
            
            if not available:
                next_arrival = min(p.arrival_time for p in processes 
                                 if p.pid not in completed)
                current_time = next_arrival
                continue
            
            proc = min(available, key=lambda p: p.burst_time)
            
            response_time = current_time - proc.arrival_time
            total_response += response_time
            
            if len(completed) > 0:
                current_time += self.context_switch_cost
                context_switches += 1
            
            timeline.append({
                'pid': proc.pid,
                'start': current_time,
                'end': current_time + proc.burst_time
            })
            current_time += proc.burst_time
            
            turnaround_time = current_time - proc.arrival_time
            wait_time = turnaround_time - proc.burst_time
            
            total_wait += wait_time
            total_turnaround += turnaround_time
            completed.add(proc.pid)
        
        n = len(processes)
        # CORREÇÃO: Chamar a função para calcular a vazão
        throughput = self._calculate_throughput(timeline)
        
        return {
            'algorithm': 'SJF',
            'quantum': '-',
            'avg_wait_time': total_wait / n,
            'avg_turnaround_time': total_turnaround / n,
            'avg_response_time': total_response / n,
            'throughput': throughput, # CORREÇÃO: Usar o valor calculado
            'context_switches': context_switches,
            'timeline': timeline
        }
    
    def simulate_rr(self, quantum: int) -> Dict:
        """Round Robin com quantum especificado"""
        processes = [Process(p.pid, p.arrival_time, p.burst_time) 
                    for p in self.processes]
        processes.sort(key=lambda p: p.arrival_time)
        
        current_time = 0
        total_wait = 0
        total_turnaround = 0
        total_response = 0
        context_switches = 0
        timeline = []
        queue = []
        idx = 0
        completed = 0
        last_pid = None
        
        while completed < len(processes):
            while idx < len(processes) and processes[idx].arrival_time <= current_time:
                queue.append(processes[idx])
                idx += 1
            
            if not queue:
                if idx < len(processes):
                    current_time = processes[idx].arrival_time
                continue
            
            proc = queue.pop(0)
            
            if proc.first_response == -1:
                proc.first_response = current_time
                total_response += current_time - proc.arrival_time
            
            # A troca de contexto deve ser antes da execução
            if last_pid is not None and last_pid != proc.pid:
                current_time += self.context_switch_cost
                context_switches += 1
            elif last_pid is None: # Primeira execução de processo
                last_pid = proc.pid

            exec_time = min(quantum, proc.remaining_time)
            timeline.append({
                'pid': proc.pid,
                'start': current_time,
                'end': current_time + exec_time
            })
            
            current_time += exec_time
            proc.remaining_time -= exec_time
            last_pid = proc.pid # Atualiza o último processo que executou
            
            while idx < len(processes) and processes[idx].arrival_time <= current_time:
                queue.append(processes[idx])
                idx += 1
            
            if proc.remaining_time > 0:
                queue.append(proc)
            else:
                turnaround_time = current_time - proc.arrival_time
                wait_time = turnaround_time - proc.burst_time
                total_wait += wait_time
                total_turnaround += turnaround_time
                completed += 1
        
        n = len(processes)
        # CORREÇÃO: Chamar a função para calcular a vazão
        throughput = self._calculate_throughput(timeline)

        return {
            'algorithm': 'RR',
            'quantum': quantum,
            'avg_wait_time': total_wait / n,
            'avg_turnaround_time': total_turnaround / n,
            'avg_response_time': total_response / n,
            'throughput': throughput, # CORREÇÃO: Usar o valor calculado
            'context_switches': context_switches,
            'timeline': timeline
        }
   
    def run_all_simulations(self) -> List[Dict]:
        """Executa todas as simulações configuradas"""
        results = []
        
        metadata = self.config.get('metadata', {})
        algorithms = metadata.get('algorithms', [])
        
        for algo in algorithms:
            if algo == 'FCFS':
                results.append(self.simulate_fcfs())
            elif algo == 'SJF':
                results.append(self.simulate_sjf())
            elif algo == 'RR':
                quantums = metadata.get('rr_quantums', [])
                for q in quantums:
                    results.append(self.simulate_rr(q))
        
        return results
    
    def print_results(self, results: List[Dict]):
        """Imprime resultados formatados"""
        print("\n" + "="*100)
        print("RESULTADOS DA SIMULAÇÃO DE ESCALONAMENTO")
        print("="*100 + "\n")
        
        print(f"{'Algoritmo':<12} {'Quantum':<10} {'Tempo Espera':<15} {'Tempo Retorno':<15} "
              f"{'Tempo Resposta':<17} {'Vazão (p/tick)':<18} {'Trocas Ctx':<12}")
        print("-"*110)
        
        for r in results:
            algo_name = f"{r['algorithm']}" if r['quantum'] == '-' else f"{r['algorithm']}(q={r['quantum']})"
            print(f"{algo_name:<12} {str(r['quantum']):<10} "
                  f"{r['avg_wait_time']:<15.2f} {r['avg_turnaround_time']:<15.2f} "
                  f"{r['avg_response_time']:<17.2f} {r['throughput']:<18.3f} " # Ajustado para float
                  f"{r['context_switches']:<12}")
        
        print("\n" + "="*100)
        
        print("\nANÁLISE COMPARATIVA:")
        print("-"*100)
        
        if not results:
            print("Nenhum resultado para analisar.")
            return

        best_wait = min(results, key=lambda x: x['avg_wait_time'])
        print(f"✓ Menor tempo médio de espera: {best_wait['algorithm']}" + 
              (f" (quantum={best_wait['quantum']})" if best_wait['quantum'] != '-' else '') +
              f" com {best_wait['avg_wait_time']:.2f} ticks")
        
        best_turnaround = min(results, key=lambda x: x['avg_turnaround_time'])
        print(f"✓ Menor tempo médio de retorno: {best_turnaround['algorithm']}" + 
              (f" (quantum={best_turnaround['quantum']})" if best_turnaround['quantum'] != '-' else '') +
              f" com {best_turnaround['avg_turnaround_time']:.2f} ticks")
        
        best_response = min(results, key=lambda x: x['avg_response_time'])
        print(f"✓ Menor tempo médio de resposta: {best_response['algorithm']}" + 
              (f" (quantum={best_response['quantum']})" if best_response['quantum'] != '-' else '') +
              f" com {best_response['avg_response_time']:.2f} ticks")
        
        min_switches = min(results, key=lambda x: x['context_switches'])
        print(f"✓ Menos trocas de contexto: {min_switches['algorithm']}" + 
              (f" (quantum={min_switches['quantum']})" if min_switches['quantum'] != '-' else '') +
              f" com {min_switches['context_switches']} trocas")
        
        print("-"*104)


def main():
    # Configuração de exemplo
    config = {
        "spec_version": "1.0",
        "challenge_id": "os_rr_fcfs_sjf_demo_manual_1",
        "metadata": {
            "context_switch_cost": 1,
            "throughput_window_T": 20,
            "algorithms": ["FCFS", "SJF", "RR"],
            "rr_quantums": [2, 4, 8]
        },
        "workload": {
            "time_unit": "ticks",
            "processes": [
              { "pid": "P01", "arrival_time": 0,  "burst_time": 6 },
              { "pid": "P02", "arrival_time": 1,  "burst_time": 3 },
              { "pid": "P03", "arrival_time": 2,  "burst_time": 8 },
              { "pid": "P04", "arrival_time": 4,  "burst_time": 4 },
              { "pid": "P05", "arrival_time": 6,  "burst_time": 5 }
            ]
        }
    }
    
    # Ou carregar de arquivo JSON
    # try:
    #     with open('config.json', 'r') as f:
    #         config = json.load(f)
    # except FileNotFoundError:
    #     print("Arquivo 'config.json' não encontrado. Usando configuração de exemplo.")

    simulator = SchedulingSimulator(config)
    results = simulator.run_all_simulations()
    simulator.print_results(results)
    
    # Opcional: Salvar resultados em JSON
    # with open('results.json', 'w') as f:
    #     json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()