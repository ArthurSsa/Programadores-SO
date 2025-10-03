import threading
import time
from typing import Dict
from dataclasses import dataclass, field
from collections import deque

@dataclass
class Animal:
    id: str
    species: str
    arrival_time: int
    rest_duration: int
    entry_time: int = -1
    exit_time: int = -1
    
    def __lt__(self, other):
        if self.arrival_time != other.arrival_time:
            return self.arrival_time < other.arrival_time
        return self.id < other.id


class VeterinaryRoomSimulator:
    def __init__(self, config: dict):
        self.config = config
        self.room_count = config['metadata']['room_count']
        self.allowed_states = config['metadata']['allowed_states']
        self.queue_policy = config['metadata']['queue_policy']
        self.sign_change_latency = config['metadata']['sign_change_latency']
        self.initial_sign = config['room']['initial_sign_state']
        self.current_sign = self.initial_sign
        self.animals_in_room = []
        self.waiting_queue = deque()
        self.completed_animals = []
        self.sign_changes = 0
        self.current_time = 0
        self.lock = threading.Lock()
        self.room_available = threading.Condition(self.lock)
        self.simulation_started = threading.Event()
        
        # Métricas
        self.total_wait_time = 0
        self.total_turnaround_time = 0
        self.timeline = []
        self.animals = [
            Animal(
                id=a['id'],
                species=a['species'],
                arrival_time=a['arrival_time'],
                rest_duration=a['rest_duration']
            )
            for a in config['workload']['animals']
        ]
        
    def can_enter_room(self, animal: Animal) -> bool:
        """Verifica se um animal pode entrar na sala (deve ser chamado com lock)"""
        if len(self.animals_in_room) == 0:
            return True
        
        for room_animal in self.animals_in_room:
            if animal.species != room_animal.species:
                return False
        
        return True
    
    def animal_thread(self, animal: Animal):
        self.simulation_started.wait()
        
        # Aguarda até o tempo de chegada
        arrival_sleep = animal.arrival_time * 0.1  # 0.1 segundos por tick
        time.sleep(arrival_sleep)
        
        with self.lock:
            print(f"[Tick {animal.arrival_time}] chegada: {animal.id} ({animal.species})")
            self.waiting_queue.append(animal)
            self.room_available.notify_all()
    
        entered = False
        while not entered:
            with self.lock:
                # Verifica se pode entrar
                if self.can_enter_room(animal) and animal in self.waiting_queue:
                    # Verifica se é sua vez na fila
                    can_enter = False
                    if self.queue_policy == "FIFO":
                        if self.waiting_queue and self.waiting_queue[0] == animal:
                            can_enter = True
                    else:
                        can_enter = True
                    
                    if can_enter:
                        self.waiting_queue.remove(animal)
                        
                        if self.current_sign == "EMPTY":
                            old_sign = self.current_sign
                            self.current_sign = animal.species
                            self.sign_changes += 1
                            print(f"PLACA {old_sign} → {self.current_sign}")
                            
                           
                            if self.sign_change_latency > 0:
                                time.sleep(self.sign_change_latency * 0.1)
                        
                        animal.entry_time = int(time.time() * 10 - self.start_time * 10)
                        self.animals_in_room.append(animal)
                        print(f"Entrada {animal.id} ({animal.species}) entrou na sala")
                        print(f"Na sala: {', '.join([a.id for a in self.animals_in_room])}")
                        print(f"Na fila: {', '.join([a.id for a in self.waiting_queue]) if self.waiting_queue else 'VAZIA'}")
                        
                        entered = True
                
                        self.room_available.notify_all()
                    else:
                        self.room_available.wait()
                else:
                    self.room_available.wait()
        
 
        rest_sleep = animal.rest_duration * 0.1
        time.sleep(rest_sleep)
        
        with self.lock:
            animal.exit_time = int(time.time() * 10 - self.start_time * 10)
            self.animals_in_room.remove(animal)
            self.completed_animals.append(animal)
            
            print(f"Saida {animal.id} ({animal.species}) saiu da sala")
            
            if len(self.animals_in_room) == 0 and self.current_sign != "EMPTY":
                old_sign = self.current_sign
                self.current_sign = "EMPTY"
                self.sign_changes += 1
                print(f"Placa {old_sign} → {self.current_sign}")

            wait_time = animal.entry_time - animal.arrival_time
            turnaround_time = animal.exit_time - animal.arrival_time
            
            self.total_wait_time += wait_time
            self.total_turnaround_time += turnaround_time
            
            self.timeline.append({
                'animal_id': animal.id,
                'species': animal.species,
                'arrival': animal.arrival_time,
                'entry': animal.entry_time,
                'exit': animal.exit_time,
                'wait_time': wait_time,
                'turnaround_time': turnaround_time
            })
            
            self.room_available.notify_all()
    
    def simulate(self) -> Dict:
        print("="*80)
        print("INICIANDO SIMULAÇÃO COM THREADING")
        print("="*80)
        
        self.start_time = time.time()
        
        threads = []
        for animal in self.animals:
            thread = threading.Thread(target=self.animal_thread, args=(animal,))
            thread.daemon = True
            threads.append(thread)
            thread.start()
        
        self.simulation_started.set()
        
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        total_time = int((end_time - self.start_time) * 10)
        
        n = len(self.animals)
        return {
            'total_animals': n,
            'avg_wait_time': self.total_wait_time / n if n > 0 else 0,
            'avg_turnaround_time': self.total_turnaround_time / n if n > 0 else 0,
            'total_sign_changes': self.sign_changes,
            'total_time': total_time,
            'timeline': sorted(self.timeline, key=lambda x: x['arrival'])
        }
    
    def print_results(self, results: Dict):
        print("\n" + "="*100)
        print("RESUMO FINAL DA SIMULAÇÃO")
        print("="*100)
        print("Métricas gerais:")
        print(f"  • Total de animais processados: {results['total_animals']}")
        print(f"  • Tempo médio de espera: {results['avg_wait_time']:.2f} ticks")
        print(f"  • Tempo médio de retorno: {results['avg_turnaround_time']:.2f} ticks")
        print(f"  • Total de trocas de placa: {results['total_sign_changes']}")
        print(f"  • Tempo total de simulação: {results['total_time']} ticks")
        print("\n" + "="*100)
        print("Timeline de animais:")
        for entry in results['timeline']:
            print(f"  {entry['animal_id']:4s} ({entry['species']:3s}): "
                  f"Chegada={entry['arrival']:3d}, Entrada={entry['entry']:3d}, "
                  f"Saída={entry['exit']:3d}, Espera={entry['wait_time']:3d}, "
                  f"Retorno={entry['turnaround_time']:3d}")


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
    
    print("\nFim da simulação")

if __name__ == "__main__":
    main()