import json
from typing import List, Dict
from dataclasses import dataclass
from collections import deque

@dataclass
class Animal:
    id: str
    species: str
    arrival_time: int
    rest_duration: int
    remaining_rest: int = 0
    entry_time: int = -1
    exit_time: int = -1
    
    def __post_init__(self):
        self.remaining_rest = self.rest_duration

class VeterinaryRoomSimulator:
    def __init__(self, config: dict):
        self.config = config
        self.room_count = config['room']['room_count']
        self.allowed_states = config['room']['allowed_states']
        self.queue_policy = config['room']['queue_policy']
        self.sign_change_latency = config['room']['sign_change_latency']
        self.tie_breaker = config['room'].get('tie_breaker', ['arrival_time', 'id'])
        self.initial_sign = config['room']['initial_sign_state']
        
        self.animals = [
            Animal(
                id=a['id'],
                species=a['species'],
                arrival_time=a['arrival_time'],
                rest_duration=a['rest_duration']
            )
            for a in config['workload']['animals']
        ]
        
    def can_enter_room(self, animal: Animal, current_sign: str, animals_in_room: List[Animal]) -> bool:
        """Verifica se um animal pode entrar na sala"""
        # Sala cheia
        if len(animals_in_room) >= self.room_count:
            return False
        
        # Verifica se a espécie está nos estados permitidos
        if animal.species not in self.allowed_states:
            return False
        
        # Se sala vazia, pode entrar
        if current_sign == "EMPTY":
            return True
        
        # Placa deve corresponder à espécie
        if current_sign != animal.species:
            return False
        
        # Verifica se há conflito de espécies na sala
        for room_animal in animals_in_room:
            # Cachorros e gatos não podem estar juntos
            if (animal.species == "DOG" and room_animal.species == "CAT") or \
               (animal.species == "CAT" and room_animal.species == "DOG"):
                return False
        
        return True
    
    def simulate(self) -> Dict:
        """Simula o protocolo da sala de repouso veterinária"""
        current_time = 0
        current_sign = self.initial_sign
        animals_in_room = []
        waiting_queue = deque()
        completed_animals = []
        
        # Métricas
        total_wait_time = 0
        total_turnaround_time = 0
        sign_changes = 0
        timeline = []
        
        
        animals = sorted(self.animals, key=lambda a: (a.arrival_time, a.id))
        animal_idx = 0
        
        max_iterations = 10000  # Proteção contra loop infinito
        iterations = 0
        
        while (len(completed_animals) < len(animals)) and iterations < max_iterations:
            iterations += 1
            
            while animal_idx < len(animals) and animals[animal_idx].arrival_time <= current_time:
                waiting_queue.append(animals[animal_idx])
                animal_idx += 1
            
            
            animals_to_remove = []
            for animal in animals_in_room:
                if animal.remaining_rest <= 0:
                    animals_to_remove.append(animal)
            
            for animal in animals_to_remove:
                animal.exit_time = current_time
                animals_in_room.remove(animal)
                completed_animals.append(animal)
                
                turnaround = animal.exit_time - animal.arrival_time
                wait = animal.entry_time - animal.arrival_time
                total_turnaround_time += turnaround
                total_wait_time += wait
                
                timeline.append({
                    'animal_id': animal.id,
                    'species': animal.species,
                    'arrival': animal.arrival_time,
                    'entry': animal.entry_time,
                    'exit': animal.exit_time,
                    'wait_time': wait,
                    'turnaround_time': turnaround
                })
            
            
            if len(animals_in_room) == 0 and current_sign != "EMPTY":
                current_sign = "EMPTY"
                sign_changes += 1
            
            
            if waiting_queue:
                # Organizar fila conforme política
                if self.queue_policy == "FIFO":
                    candidates = list(waiting_queue)
                else:  # PRIORITY ou outra política
                    candidates = sorted(
                        waiting_queue,
                        key=lambda a: (
                            0 if a.species == current_sign else 1,
                            a.arrival_time,
                            a.id
                        )
                    )
                
                for animal in candidates:
                    if self.can_enter_room(animal, current_sign, animals_in_room):
                        # Mudar placa se necessário
                        if current_sign == "EMPTY":
                            if self.sign_change_latency > 0:
                                current_time += self.sign_change_latency
                            current_sign = animal.species
                            sign_changes += 1
                        
                        # Animal entra na sala
                        animal.entry_time = current_time
                        animals_in_room.append(animal)
                        waiting_queue.remove(animal)
            
            if animals_in_room:
                # Processar 1 tick de descanso para cada animal na sala
                for animal in animals_in_room:
                    animal.remaining_rest -= 1
                current_time += 1
            elif waiting_queue:
                current_time += 1
            elif animal_idx < len(animals):
                # Ninguém na sala, ninguém esperando - pular para próxima chegada
                current_time = animals[animal_idx].arrival_time
            else:
                break
        
        if iterations >= max_iterations:
            print("AVISO: Número máximo de iterações atingido!")
        
        n = len(animals)
        return {
            'total_animals': n,
            'avg_wait_time': total_wait_time / n if n > 0 else 0,
            'avg_turnaround_time': total_turnaround_time / n if n > 0 else 0,
            'total_sign_changes': sign_changes,
            'total_time': current_time,
            'timeline': timeline
        }
    
    def print_results(self, results: Dict):
        """Imprime resultados formatados"""
        print("\n" + "="*100)
        print("SIMULAÇÃO DO PROTOCOLO DA SALA DE REPOUSO VETERINÁRIA")
        print("="*100 + "\n")
        
        print(f"{'ID':<8} {'Espécie':<10} {'Chegada':<10} {'Entrada':<10} {'Saída':<10} "
              f"{'Espera':<10} {'Retorno':<10}")
        print("-"*100)
        
        for entry in sorted(results['timeline'], key=lambda x: x['arrival']):
            print(f"{entry['animal_id']:<8} {entry['species']:<10} "
                  f"{entry['arrival']:<10} {entry['entry']:<10} {entry['exit']:<10} "
                  f"{entry['wait_time']:<10} {entry['turnaround_time']:<10}")
        
        print("\n" + "="*100)
        print("Metrica gerais:")
        print("-"*100)
        print(f"  • Total de animais processados: {results['total_animals']}")
        print(f"  • Tempo medio de espera: {results['avg_wait_time']:.2f} ticks")
        print(f"  • Tempo medio de retorno: {results['avg_turnaround_time']:.2f} ticks")
        print(f"  • Total de trocas de placa: {results['total_sign_changes']}")
        print(f"  • Tempo total de simulação: {results['total_time']} ticks")
        print("="*100 + "\n")
        
        # Análise por espécie
        species_stats = {}
        for entry in results['timeline']:
            species = entry['species']
            if species not in species_stats:
                species_stats[species] = {
                    'count': 0,
                    'total_wait': 0,
                    'total_turnaround': 0
                }
            species_stats[species]['count'] += 1
            species_stats[species]['total_wait'] += entry['wait_time']
            species_stats[species]['total_turnaround'] += entry['turnaround_time']
        
        if species_stats:
            print("Analise por especie:")
            print("-"*100)
            for species, stats in species_stats.items():
                count = stats['count']
                avg_wait = stats['total_wait'] / count
                avg_turnaround = stats['total_turnaround'] / count
                print(f"  {species}:")
                print(f"    - Total: {count} animal(is)")
                print(f"    - Tempo medio de espera: {avg_wait:.2f} ticks")
                print(f"    - Tempo medio de retorno: {avg_turnaround:.2f} ticks")
            print("="*100 + "\n")

def main():
    config = {
        "spec_version": "1.0",
        "challenge_id": "vet-room-protocol-demo",
        "metadata": {},
        "room": {
            "room_count": 1,
            "allowed_states": ["EMPTY", "DOG", "CAT"],
            "queue_policy": "FIFO",
            "sign_change_latency": 0,
            "tie_breaker": ["arrival_time", "id"],
            "initial_sign_state": "EMPTY"
        },
        "workload": {
            "time_unit": "ticks",
            "animals": [
                {"id": "D01", "species": "DOG", "arrival_time": 0, "rest_duration": 5},
                {"id": "C01", "species": "CAT", "arrival_time": 1, "rest_duration": 4},
                {"id": "D02", "species": "DOG", "arrival_time": 2, "rest_duration": 6},
                {"id": "C02", "species": "CAT", "arrival_time": 3, "rest_duration": 2},
                {"id": "D03", "species": "DOG", "arrival_time": 4, "rest_duration": 3}
            ]
        }
    }
    print("Iniciando simulação...")
    
    simulator = VeterinaryRoomSimulator(config)
    results = simulator.simulate()
    simulator.print_results(results)
    
    print("fim")

if __name__ == "__main__":
    main()