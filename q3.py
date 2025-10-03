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
        self.room_count = config['metadata']['room_count']
        self.allowed_states = config['metadata']['allowed_states']
        self.queue_policy = config['metadata']['queue_policy']
        self.sign_change_latency = config['metadata']['sign_change_latency']
        self.tie_breaker = config['metadata'].get('tie_breaker', ['arrival_time', 'id'])
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
        if len(animals_in_room) == 0:
            return True
        
        for room_animal in animals_in_room:
            if animal.species != room_animal.species:
                return False
        
        return True
    
    def simulate(self) -> Dict:
        """Simula o protocolo da sala de repouso veterinária com output tick por tick"""
        current_time = 0
        current_sign = self.initial_sign
        animals_in_room = []
        waiting_queue = deque()
        completed_animals = []
        
        total_wait_time = 0
        total_turnaround_time = 0
        sign_changes = 0
        timeline = []
        animals = sorted(self.animals, key=lambda a: (a.arrival_time, a.id))
        animal_idx = 0
        max_iterations = 10000
        iterations = 0
        
        while (len(completed_animals) < len(animals)) and iterations < max_iterations:
            iterations += 1

            print(f"")
            print(f" TICK {current_time}")
            
            # Adicionar animais que chegaram à fila de espera
            new_arrivals = []
            while animal_idx < len(animals) and animals[animal_idx].arrival_time <= current_time:
                new_arrivals.append(animals[animal_idx])
                waiting_queue.append(animals[animal_idx])
                animal_idx += 1
            
            if new_arrivals:
                print(f" CHEGADAS: {', '.join([f'{a.id} ({a.species})' for a in new_arrivals])}")
            
            # Remover animais que terminaram o descanso
            animals_to_remove = []
            for animal in animals_in_room:
                if animal.remaining_rest <= 0:
                    animals_to_remove.append(animal)
            
            if animals_to_remove:
                print(f"SAÍDAS: {', '.join([f'{a.id} ({a.species})' for a in animals_to_remove])}")
            
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
            
            # Atualizar placa se sala ficou vazia
            if len(animals_in_room) == 0 and current_sign != "EMPTY":
                old_sign = current_sign
                current_sign = "EMPTY"
                sign_changes += 1
                print(f" PLACA MUDOU: {old_sign} → {current_sign}")
            
            # Tentar admitir animais da fila
            admitted_animals = []
            if waiting_queue:
                if self.queue_policy == "FIFO":
                    candidates = list(waiting_queue)
                else:
                    candidates = sorted(
                        waiting_queue,
                        key=lambda a: (
                            0 if a.species == current_sign else 1,
                            a.arrival_time,
                            a.id
                        )
                    )
                
                for animal in candidates[:]:
                    if self.can_enter_room(animal, current_sign, animals_in_room):
                        if current_sign == "EMPTY":
                            if self.sign_change_latency > 0:
                                current_time += self.sign_change_latency
                            old_sign = current_sign
                            current_sign = animal.species
                            sign_changes += 1
                            print(f" PLACA MUDOU: {old_sign} → {current_sign}")
                        
                        animal.entry_time = current_time
                        animals_in_room.append(animal)
                        waiting_queue.remove(animal)
                        admitted_animals.append(animal)
            
            if admitted_animals:
                print(f" ENTRARAM: {', '.join([f'{a.id} ({a.species})' for a in admitted_animals])}")
            
            print(f"\nSTATUS ATUAL:")
            print(f"    Placa: {current_sign}")
            print(f"    Na sala: {', '.join([f'{a.id}({a.remaining_rest})' for a in animals_in_room]) if animals_in_room else 'VAZIA'}")
            print(f"    Na fila: {', '.join([f'{a.id}({a.species})' for a in waiting_queue]) if waiting_queue else 'VAZIA'}")
            
            if animals_in_room:
                for animal in animals_in_room:
                    animal.remaining_rest -= 1
                current_time += 1
            elif waiting_queue:
                if animal_idx < len(animals):
                    current_time = min(current_time + 1, animals[animal_idx].arrival_time)
                else:
                    current_time += 1
            elif animal_idx < len(animals):
                print(f"PULANDO para próxima chegada (tick {animals[animal_idx].arrival_time})")
                current_time = animals[animal_idx].arrival_time
            else:
                break
        
        if iterations >= max_iterations:
            print("\n AVISO: Numero maximo de iterações atingido!")
        
        
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
        print("RESUMO FINAL DA SIMULAÇÃO")
        print("\n" + "="*100)
        print("Metricas gerais:")
        print("-"*100)
        print(f"  • Total de animais processados: {results['total_animals']}")
        print(f"  • Tempo medio de espera: {results['avg_wait_time']:.2f} ticks")
        print(f"  • Tempo medio de retorno: {results['avg_turnaround_time']:.2f} ticks")
        print(f"  • Total de trocas de placa: {results['total_sign_changes']}")
        print(f"  • Tempo total de simulação: {results['total_time']} ticks")
        print("\n")

def main():
    config = {
        "spec_version": "1.0",
        "challenge_id": "vet_room_protocol_demo_v3_mixed_arrivals",
        "metadata": {
            "room_count": 1,
            "allowed_states": ["EMPTY", "DOGS", "CATS"],
            "queue_policy": "FIFO",
            "sign_change_latency": 0,
            "tie_breaker": ["arrival_time", "id"]
        },
        "room": {
            "initial_sign_state": "EMPTY"
        },
        "workload": {
            "time_unit": "ticks",
            "animals": [
                { "id": "D01", "species": "DOG", "arrival_time": 0,  "rest_duration": 6 },
                { "id": "D02", "species": "DOG", "arrival_time": 1,  "rest_duration": 5 },
                { "id": "D03", "species": "DOG", "arrival_time": 2,  "rest_duration": 7 },
                { "id": "D04", "species": "DOG", "arrival_time": 3,  "rest_duration": 4 },
                { "id": "C01", "species": "CAT", "arrival_time": 5,  "rest_duration": 6 },
                { "id": "C02", "species": "CAT", "arrival_time": 8,  "rest_duration": 3 },
                { "id": "C03", "species": "CAT", "arrival_time": 8,  "rest_duration": 5 },
                { "id": "D05", "species": "DOG", "arrival_time": 10, "rest_duration": 8 },
                { "id": "D06", "species": "DOG", "arrival_time": 11, "rest_duration": 4 },
                { "id": "D07", "species": "DOG", "arrival_time": 15, "rest_duration": 6 },
                { "id": "D08", "species": "DOG", "arrival_time": 15, "rest_duration": 3 },
                { "id": "C04", "species": "CAT", "arrival_time": 18, "rest_duration": 4 },
                { "id": "C05", "species": "CAT", "arrival_time": 20, "rest_duration": 7 },
                { "id": "C06", "species": "CAT", "arrival_time": 20, "rest_duration": 2 },
                { "id": "D09", "species": "DOG", "arrival_time": 22, "rest_duration": 5 },
                { "id": "C07", "species": "CAT", "arrival_time": 25, "rest_duration": 5 },
                { "id": "C08", "species": "CAT", "arrival_time": 25, "rest_duration": 6 },
                { "id": "C09", "species": "CAT", "arrival_time": 25, "rest_duration": 4 },
                { "id": "D10", "species": "DOG", "arrival_time": 26, "rest_duration": 9 },
                { "id": "D11", "species": "DOG", "arrival_time": 30, "rest_duration": 5 },
                { "id": "D12", "species": "DOG", "arrival_time": 31, "rest_duration": 4 },
                { "id": "D13", "species": "DOG", "arrival_time": 32, "rest_duration": 3 },
                { "id": "C10", "species": "CAT", "arrival_time": 35, "rest_duration": 8 },
                { "id": "C11", "species": "CAT", "arrival_time": 40, "rest_duration": 3 },
                { "id": "C12", "species": "CAT", "arrival_time": 40, "rest_duration": 5 },
                { "id": "D14", "species": "DOG", "arrival_time": 41, "rest_duration": 7 },
                { "id": "D15", "species": "DOG", "arrival_time": 55, "rest_duration": 4 },
                { "id": "D16", "species": "DOG", "arrival_time": 55, "rest_duration": 6 },
                { "id": "C13", "species": "CAT", "arrival_time": 60, "rest_duration": 7 },
                { "id": "C14", "species": "CAT", "arrival_time": 60, "rest_duration": 3 },
                { "id": "D17", "species": "DOG", "arrival_time": 68, "rest_duration": 5 }
            ]
        }
    }
    
    simulator = VeterinaryRoomSimulator(config)
    results = simulator.simulate()
    simulator.print_results(results)
    
    print("Fim da simulação")

if __name__ == "__main__":
    main()