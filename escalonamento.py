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
        self.context_switch_cost = config.get('context_switch_cost', 1)
        self.processes = [
            Process(
                pid=p['pid'],
                arrival_time=p['arrival_time'],
                burst_time=p['burst_time']
            )
            for p in config['workload']['processes']
        ]
        
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
            # Aguardar processo chegar
            if current_time < proc.arrival_time:
                current_time = proc.arrival_time
            
            # Tempo de resposta
            response_time = current_time - proc.arrival_time
            total_response += response_time
            
            # Troca de contexto (exceto primeiro processo)
            if idx > 0:
                current_time += self.context_switch_cost
                context_switches += 1
            
            # Executar processo
            timeline.append({
                'pid': proc.pid,
                'start': current_time,
                'end': current_time + proc.burst_time
            })
            current_time += proc.burst_time
            
            # Métricas
            turnaround_time = current_time - proc.arrival_time
            wait_time = turnaround_time - proc.burst_time
            
            total_wait += wait_time
            total_turnaround += turnaround_time
        
        n = len(processes)
        return {
            'algorithm': 'FCFS',
            'quantum': '-',
            'avg_wait_time': total_wait / n,
            'avg_turnaround_time': total_turnaround / n,
            'avg_response_time': total_response / n,
            'throughput': n,
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
            # Processos disponíveis
            available = [p for p in processes 
                        if p.arrival_time <= current_time and p.pid not in completed]
            
            if not available:
                # Avançar para próxima chegada
                next_arrival = min(p.arrival_time for p in processes 
                                 if p.pid not in completed)
                current_time = next_arrival
                continue
            
            # Selecionar processo com menor burst_time
            proc = min(available, key=lambda p: p.burst_time)
            
            # Tempo de resposta
            response_time = current_time - proc.arrival_time
            total_response += response_time
            
            # Troca de contexto (exceto primeiro)
            if len(completed) > 0:
                current_time += self.context_switch_cost
                context_switches += 1
            
            # Executar processo
            timeline.append({
                'pid': proc.pid,
                'start': current_time,
                'end': current_time + proc.burst_time
            })
            current_time += proc.burst_time
            
            # Métricas
            turnaround_time = current_time - proc.arrival_time
            wait_time = turnaround_time - proc.burst_time
            
            total_wait += wait_time
            total_turnaround += turnaround_time
            completed.add(proc.pid)
        
        n = len(processes)
        return {
            'algorithm': 'SJF',
            'quantum': '-',
            'avg_wait_time': total_wait / n,
            'avg_turnaround_time': total_turnaround / n,
            'avg_response_time': total_response / n,
            'throughput': n,
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
            # Adicionar processos que chegaram à fila
            while idx < len(processes) and processes[idx].arrival_time <= current_time:
                queue.append(processes[idx])
                idx += 1
            
            if not queue:
                # Fila vazia, avançar para próxima chegada
                current_time = processes[idx].arrival_time
                continue
            
            # Pegar próximo processo da fila
            proc = queue.pop(0)
            
            # Registrar tempo de resposta na primeira execução
            if proc.first_response == -1:
                proc.first_response = current_time
                total_response += current_time - proc.arrival_time
            
            # Troca de contexto (se mudou de processo)
            if last_pid is not None and last_pid != proc.pid:
                current_time += self.context_switch_cost
                context_switches += 1
            
            # Executar por quantum ou tempo restante
            exec_time = min(quantum, proc.remaining_time)
            timeline.append({
                'pid': proc.pid,
                'start': current_time,
                'end': current_time + exec_time
            })
            
            current_time += exec_time
            proc.remaining_time -= exec_time
            last_pid = proc.pid
            
            # Adicionar novos processos que chegaram durante execução
            while idx < len(processes) and processes[idx].arrival_time <= current_time:
                queue.append(processes[idx])
                idx += 1
            
            if proc.remaining_time > 0:
                # Processo não terminou, volta para fila
                queue.append(proc)
            else:
                # Processo concluído
                turnaround_time = current_time - proc.arrival_time
                wait_time = turnaround_time - proc.burst_time
                total_wait += wait_time
                total_turnaround += turnaround_time
                completed += 1
        
        n = len(processes)
        return {
            'algorithm': 'RR',
            'quantum': quantum,
            'avg_wait_time': total_wait / n,
            'avg_turnaround_time': total_turnaround / n,
            'avg_response_time': total_response / n,
            'throughput': n,
            'context_switches': context_switches,
            'timeline': timeline
        }
    
    def run_all_simulations(self) -> List[Dict]:
        """Executa todas as simulações configuradas"""
        results = []
        algorithms = self.config.get('algorithms', [])
        
        for algo in algorithms:
            if algo == 'FCFS':
                results.append(self.simulate_fcfs())
            elif algo == 'SJF':
                results.append(self.simulate_sjf())
            elif algo == 'RR':
                quantums = self.config.get('rr_quantums', [])
                for q in quantums:
                    results.append(self.simulate_rr(q))
        
        return results
    
    def print_results(self, results: List[Dict]):
        """Imprime resultados formatados"""
        print("\n" + "="*100)
        print("RESULTADOS DA SIMULAÇÃO DE ESCALONAMENTO")
        print("="*100 + "\n")
        
        # Cabeçalho
        print(f"{'Algoritmo':<12} {'Quantum':<10} {'Tempo Espera':<15} {'Tempo Retorno':<15} "
              f"{'Tempo Resposta':<17} {'Vazão':<8} {'Trocas Ctx':<12}")
        print("-"*100)
        
        # Resultados
        for r in results:
            algo_name = f"{r['algorithm']}" if r['quantum'] == '-' else f"{r['algorithm']}(q={r['quantum']})"
            print(f"{algo_name:<12} {str(r['quantum']):<10} "
                  f"{r['avg_wait_time']:<15.2f} {r['avg_turnaround_time']:<15.2f} "
                  f"{r['avg_response_time']:<17.2f} {r['throughput']:<8} "
                  f"{r['context_switches']:<12}")
        
        print("\n" + "="*100)
        
        # Análise comparativa
        print("\nANÁLISE COMPARATIVA:")
        print("-"*100)
        
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
        
        print("="*100 + "\n")


def main():
    # Configuração de exemplo
    config = {
        "spec_version": "1.0",
        "challenge_id": "rr-fcfs-sjf-demo",
        "metadata": {},
        "context_switch_cost": 1,
        "throughput_window_T": 100,
        "algorithms": ["FCFS", "SJF", "RR"],
        "rr_quantums": [1, 2, 4, 8, 16],
        "workload": {
            "time_unit": "ticks",
            "processes": [
                {"pid": "P01", "arrival_time": 0, "burst_time": 5},
                {"pid": "P02", "arrival_time": 1, "burst_time": 17},
                {"pid": "P03", "arrival_time": 2, "burst_time": 3},
                {"pid": "P04", "arrival_time": 4, "burst_time": 22},
                {"pid": "P05", "arrival_time": 6, "burst_time": 7}
            ]
        }
    }
    
    # Ou carregar de arquivo JSON
    # with open('config.json', 'r') as f:
    #     config = json.load(f)
    
    # Executar simulação
    simulator = SchedulingSimulator(config)
    results = simulator.run_all_simulations()
    simulator.print_results(results)
    
    # Opcional: Salvar resultados em JSON
    # with open('results.json', 'w') as f:
    #     json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()
