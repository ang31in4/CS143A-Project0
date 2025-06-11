from io import TextIOWrapper
import json
from dataclasses import dataclass
from pathlib import Path
import sys

from kernel import Kernel, MMU

MICRO_S = int
PID = int

NUM_MICRO_IN_SEC: MICRO_S = 1000000
TIMER_INTERRUPT_INTERVAL: MICRO_S = 10
MB_TO_BYTES: int = 1048576

VALID_SCHEDULING_ALGORITHMS = {"FCFS", "Priority", "RR", "Multilevel"}
VALID_PROCESS_TYPES = {"Foreground", "Background"}

PROCESSES: str = "processes"
ARRIVAL: str = "arrival"
TOTAL_CPU_TIME: str = "total_cpu_time"
PRIORITY: str = "priority"
PRIORITY_CHANGES: str = "priority_change"
EVENT_ARRIVAL: str = "arrival"
NEW_PRIORITY: str = "new_priority"
SEMAPHORES: str = "semaphores"
SEMAPHORE_ID: str = "id"
SEMAPHORE_INIT_VAL: str = "init_val"
PROCESS_SEMAPHORE: str = "semaphore"
PROCESSES_SEMA_ID: str = "id"
PROCESS_SEMA_P: str = "p"
PROCESS_SEMA_V: str = "v"
MUTEXES: str = "mutexes"
PROCESS_MUTEX: str = "mutex"
PROCESSES_MUTEX_ID: str = "id"
PROCESS_MUTEX_LOCK: str = "lock"
PROCESS_MUTEX_UNLOCK: str = "unlock"
PROCESS_TYPE: str = "type"
PROCESS_MEMORY_ACCESS: str = "memory_access"
PROCESS_MEMORY_NEEDED: str = "needed_memory_MB"
MEMORY_SIZE: str = "memory_size_MB"

DEFAULT_PRIORITY = 32

class SimulationError(Exception):
    pass

@dataclass
class PriorityChangeEvent:
    arrival: MICRO_S
    new_priority: int

@dataclass
class SemaphoreCallEvent:
    arrival: MICRO_S
    id: int

@dataclass
class MutexEvent:
    arrival: MICRO_S
    id: int

@dataclass
class Semaphore:
    init_val: int
    initilized: bool

@dataclass
class Mutex:
    initilized: bool

@dataclass
class MemoryEvent:
    arrival: MICRO_S
    address: int

@dataclass
class Process:
    arrival: MICRO_S
    total_cpu_time: MICRO_S
    elapsed_cpu_time: MICRO_S
    priority: int
    priority_change_events: list[PriorityChangeEvent]
    semaphore_p_events: list[SemaphoreCallEvent]
    semaphore_v_events: list[SemaphoreCallEvent]
    mutex_lock_events: list[MutexEvent]
    mutex_unlock_events: list[MutexEvent]
    process_type: str
    memory_needed: int
    memory_events: list[MemoryEvent]

class Simulator:
    elapsed_time: MICRO_S
    current_process: PID
    processes: dict[PID, Process]
    arrivals: list[Process]
    kernel: Kernel
    next_pid: PID
    simlog: TextIOWrapper
    needs_spacing: False
    process_0_runtime: MICRO_S
    semaphores: dict[int, Semaphore]
    mutexes: dict[int, Mutex]
    student_logs: "StudentLogger"
    mmu: MMU

    def __init__(self, emulation_description_path: Path, logfile_path: str, student_logs: bool):
        self.elapsed_time = 0
        self.current_process = 0
        self.processes = dict()
        self.arrivals = []
        self.next_pid = 1
        self.needs_spacing = False
        self.process_0_runtime = 0
        self.semaphores = dict()
        self.mutexes = dict()
        if student_logs:
            self.student_logs = StudentLogger(self)
        else:
            self.student_logs = StudentLogger(None)

        emulation_json = None
        with open(emulation_description_path, 'r') as file:
            emulation_json = json.load(file)

        if SEMAPHORES in emulation_json:
            assert(type(emulation_json[SEMAPHORES]) is list)
            for semaphore in emulation_json[SEMAPHORES]:
                assert(SEMAPHORE_ID in semaphore and type(semaphore[SEMAPHORE_ID]) is int)
                assert(SEMAPHORE_INIT_VAL in semaphore and type(semaphore[SEMAPHORE_INIT_VAL]) is int)
                assert(semaphore[SEMAPHORE_ID] not in self.semaphores)
                self.semaphores[semaphore[SEMAPHORE_ID]] = Semaphore(semaphore[SEMAPHORE_INIT_VAL], False)
        
        if MUTEXES in emulation_json:
            assert(type(emulation_json[MUTEXES]) is list)
            for mutex_id in emulation_json[MUTEXES]:
                assert(type(mutex_id) is int)
                self.mutexes[mutex_id] = Mutex(False)

        assert(PROCESSES in emulation_json and type(emulation_json[PROCESSES]) is list)
        for process in emulation_json[PROCESSES]:
            assert(ARRIVAL in process and type(process[ARRIVAL]) is MICRO_S)
            assert(TOTAL_CPU_TIME in process and type(process[TOTAL_CPU_TIME]) is MICRO_S)
            
            priority = DEFAULT_PRIORITY
            if PRIORITY in process:
                assert(type(process[PRIORITY]) is int)
                priority = process[PRIORITY]

            priority_changes = []
            if PRIORITY_CHANGES in process:
                assert(type(process[PRIORITY_CHANGES]) is list)
                for change in process[PRIORITY_CHANGES]:
                    assert(EVENT_ARRIVAL in change and type(change[EVENT_ARRIVAL]) is int)
                    assert(NEW_PRIORITY in change and type(change[NEW_PRIORITY]) is int)
                    priority_changes.append(PriorityChangeEvent(change[EVENT_ARRIVAL], change[NEW_PRIORITY]))

            semaphore_p_events = list()
            semaphore_v_events = list()
            if PROCESS_SEMAPHORE in process:
                assert(type(process[PROCESS_SEMAPHORE]) is list)
                for event in process[PROCESS_SEMAPHORE]:
                    assert(PROCESSES_SEMA_ID in event and type(event[PROCESSES_SEMA_ID]) is int)
                    id = event[PROCESSES_SEMA_ID]
                    assert(PROCESS_SEMA_P in event or PROCESS_SEMA_V in event)
                    if PROCESS_SEMA_P in event:
                        assert(type(event[PROCESS_SEMA_P]) is int)
                        semaphore_p_events.append(SemaphoreCallEvent(event[PROCESS_SEMA_P], id))
                    elif PROCESS_SEMA_V in event:
                        assert(type(event[PROCESS_SEMA_V]) is int)
                        semaphore_v_events.append(SemaphoreCallEvent(event[PROCESS_SEMA_V], id))

            mutex_lock_events = list()
            mutex_unlock_events = list()
            if PROCESS_MUTEX in process:
                assert(type(process[PROCESS_MUTEX]) is list)
                for event in process[PROCESS_MUTEX]:
                    assert(PROCESSES_MUTEX_ID in event and type(event[PROCESSES_MUTEX_ID]) is int)
                    id = event[PROCESSES_MUTEX_ID]
                    assert(PROCESS_MUTEX_LOCK in event or PROCESS_MUTEX_UNLOCK in event)
                    if PROCESS_MUTEX_LOCK in event:
                        assert(type(event[PROCESS_MUTEX_LOCK]) is int)
                        mutex_lock_events.append(MutexEvent(event[PROCESS_MUTEX_LOCK], id))
                    elif PROCESS_MUTEX_UNLOCK in event:
                        assert(type(event[PROCESS_MUTEX_UNLOCK]) is int)
                        mutex_unlock_events.append(MutexEvent(event[PROCESS_MUTEX_UNLOCK], id))

            process_type = "Foreground"
            if PROCESS_TYPE in process:
                assert(process[PROCESS_TYPE] in VALID_PROCESS_TYPES)
                process_type = process[PROCESS_TYPE]

            # Default memory needed
            memory_needed_mb = 10
            if PROCESS_MEMORY_NEEDED in process:
                assert(type(process[PROCESS_MEMORY_NEEDED]) is int)
                memory_needed_mb = process[PROCESS_MEMORY_NEEDED]

            memory_events = []
            if PROCESS_MEMORY_ACCESS in process:
                assert(type(process[PROCESS_MEMORY_ACCESS]) is list)
                for access_list in process[PROCESS_MEMORY_ACCESS]:
                    assert(type(access_list) is dict)
                    for (address_str, arrival) in access_list.items():
                        assert(type(address_str) is str and type(arrival) is int)
                        try:
                            address = int(address_str, base=0)
                        except ValueError:
                            assert(False)
                        memory_events.append(MemoryEvent(arrival, address))

            # Sort all event lists such that their last element is always the next event
            for event_list in [priority_changes, semaphore_p_events, semaphore_v_events, mutex_lock_events, mutex_unlock_events, memory_events]:
                event_list.sort(key=lambda c: c.arrival, reverse=True)


            process = Process(process[ARRIVAL], process[TOTAL_CPU_TIME], 0, priority, priority_changes, \
                              semaphore_p_events, semaphore_v_events, mutex_lock_events, mutex_unlock_events, \
                                process_type, memory_needed_mb * MB_TO_BYTES, memory_events)
            assert_events_are_valid_and_not_at_same_time(process)
            self.arrivals.append(process)
        # Sort arrivals so earliest arrivals are at the end.
        self.arrivals.sort(key=lambda p: p.arrival, reverse=True)

        # Default memory size
        memory_size_mb = 1000

        if MEMORY_SIZE in emulation_json:
            assert(type(emulation_json[MEMORY_SIZE]) is int)
            memory_size_mb = emulation_json[MEMORY_SIZE]

        self.mmu = MMU(self.student_logs)

        assert("scheduling_algorithm" in emulation_json and emulation_json["scheduling_algorithm"] in VALID_SCHEDULING_ALGORITHMS)
        self.kernel = Kernel(emulation_json["scheduling_algorithm"], self.student_logs, self.mmu, memory_size_mb * MB_TO_BYTES)

        self.simlog = open(logfile_path, 'w')

    
    def run_simulator(self):
        # Emulation ends when all processes have finished.
        while len(self.processes) + len(self.arrivals) > 0:
            if self.current_process == 0:
                self.process_0_runtime += 1
            if self.process_0_runtime >= NUM_MICRO_IN_SEC:
                raise SimulationError( \
                """Process 0 (idle process) has been running for 1 second straight. 
                This will not happen in tested simulations and is likely a bug in the kernel.""")
            
            self.advance_current_process()

            self.check_for_arrival()

            if self.elapsed_time != 0 and self.elapsed_time % TIMER_INTERRUPT_INTERVAL == 0:
                self.switch_process(self.kernel.timer_interrupt())

            self.log_add_spacing()
            self.elapsed_time += 1
        self.simlog.close()

    def advance_current_process(self):
        if self.current_process == 0:
            return
        
        current_process = self.processes[self.current_process]
        current_process.elapsed_cpu_time += 1

        # If the current_process has finished execution
        if current_process.total_cpu_time <= current_process.elapsed_cpu_time:
            self.log(f"Process {self.current_process} has finished execution and is exiting")
            self.exit_current_process()
            return


        event_list = current_process.priority_change_events
        while len(event_list) > 0 and event_list[len(event_list) - 1].arrival <= current_process.elapsed_cpu_time:
            priority_change = event_list.pop()
            self.log(f"Process {self.current_process} set priority to {priority_change.new_priority}")
            self.switch_process(self.kernel.syscall_set_priority(priority_change.new_priority))


        event_list = current_process.semaphore_p_events
        while len(event_list) > 0 and event_list[len(event_list) - 1].arrival <= current_process.elapsed_cpu_time:
            semaphore_p = event_list.pop()
            self.check_semaphore_inited(semaphore_p.id)
            self.log(f"Process {self.current_process} called p on semaphore {semaphore_p.id}")
            self.switch_process(self.kernel.syscall_semaphore_p(semaphore_p.id))
        
        event_list = current_process.semaphore_v_events
        while len(event_list) > 0 and event_list[len(event_list) - 1].arrival <= current_process.elapsed_cpu_time:
            semaphore_v = event_list.pop()
            self.check_semaphore_inited(semaphore_v.id)
            self.log(f"Process {self.current_process} called v on semaphore {semaphore_v.id}")
            self.switch_process(self.kernel.syscall_semaphore_v(semaphore_v.id))


        event_list = current_process.mutex_lock_events
        while len(event_list) > 0 and event_list[len(event_list) - 1].arrival <= current_process.elapsed_cpu_time:
            mutex_lock = event_list.pop()
            self.check_mutex_inited(mutex_lock.id)
            self.log(f"Process {self.current_process} called lock on mutex {mutex_lock.id}")
            self.switch_process(self.kernel.syscall_mutex_lock(mutex_lock.id))
        
        event_list = current_process.mutex_unlock_events
        while len(event_list) > 0 and event_list[len(event_list) - 1].arrival <= current_process.elapsed_cpu_time:
            mutex_unlock = event_list.pop()
            self.check_mutex_inited(mutex_unlock.id)
            self.log(f"Process {self.current_process} called unlock on mutex {mutex_unlock.id}")
            self.switch_process(self.kernel.syscall_mutex_unlock(mutex_unlock.id))

        event_list = current_process.memory_events
        while len(event_list) > 0 and event_list[len(event_list) - 1].arrival <= current_process.elapsed_cpu_time:
            memory_event = event_list.pop()
            translation = self.mmu.translate(memory_event.address, self.current_process)
            if translation is None:
                self.log(f"Process {self.current_process} tried to access virtual address 0x{memory_event.address:0x} which caused a segfault")
                self.log(f"Process {self.current_process} has trapped and is forcefully exiting")
                self.exit_current_process()
            else:
                self.log(f"Process {self.current_process} accessed virtual address 0x{memory_event.address:0x} which translates to physical address 0x{translation:0x}")

    def exit_current_process(self):
        new_process = self.kernel.syscall_exit()
        if new_process == self.current_process:
            raise SimulationError(f"Attempted to continue execution of exiting process (pid = {self.current_process})")
        
        del self.processes[self.current_process]
        
        self.switch_process(new_process)

    def check_semaphore_inited(self, id: int):
        if not self.semaphores[id].initilized:
            self.log(f"Semaphore {id} initilized with value {self.semaphores[id].init_val}")
            self.kernel.syscall_init_semaphore(id, self.semaphores[id].init_val)
            self.semaphores[id].initilized = True

    def check_mutex_inited(self, id: int):
        if not self.mutexes[id].initilized:
            self.log(f"Mutex {id} initilized")
            self.kernel.syscall_init_mutex(id)
            self.mutexes[id].initilized = True

    def check_for_arrival(self):
        while len(self.arrivals) > 0 and self.arrivals[len(self.arrivals) - 1].arrival == self.elapsed_time:
            new_process = self.arrivals.pop()
            self.processes[self.next_pid] = new_process
            self.log(f"{new_process.process_type} process {self.next_pid} arrived with priority {new_process.priority} requesting {new_process.memory_needed / MB_TO_BYTES}MB of memory")
            kernel_response = self.kernel.new_process_arrived(self.next_pid, new_process.priority, new_process.process_type, new_process.memory_needed)
            if kernel_response == -1:
                self.log(f"Unable to allocate memory for new process. Dropping process.")
                del self.processes[self.next_pid]
            else:
                self.switch_process(kernel_response)
            self.next_pid += 1


    def switch_process(self, new_process: int):
        if new_process != 0:
            if new_process not in self.processes:
                raise SimulationError(f"Attempted to switch to unkown PID {new_process}")
            self.process_0_runtime = 0

        if new_process != self.current_process:
            self.log(f"Context switching to pid: {new_process}")
        self.current_process = new_process

    def log(self, str: str, student_log = False):
        if student_log:
            delimiter = '#'
        else:
            delimiter = ':'
        self.simlog.write(f"{self.elapsed_time / 1000:.3f}ms {delimiter} {str}\n")
        self.needs_spacing = True
    
    def log_add_spacing(self):
        if self.needs_spacing:
            self.simlog.write("\n")
            self.needs_spacing = False

class StudentLogger:
    __simluator: Simulator

    def __init__(self, simulator: Simulator | None):
        self.__simluator = simulator

    def log(self, str: str):
        if self.__simluator is not None:
            self.__simluator.log(str, student_log=True)

# Having events at the same time as other events in the same process could cause a desync between what the simulator thinks is running and what the handler does.
# This assert ensures the process does not have this issue.
# Additionally ensures that all events will happen before the process exits.
def assert_events_are_valid_and_not_at_same_time(process: Process):
    event_arrivals = set()
    for event in process.priority_change_events:
        assert(event.arrival not in event_arrivals)
        event_arrivals.add(event.arrival)
    
    for event in process.semaphore_p_events:
        assert(event.arrival not in event_arrivals)
        event_arrivals.add(event.arrival)
    
    for event in process.semaphore_v_events:
        assert(event.arrival not in event_arrivals)
        event_arrivals.add(event.arrival)

    for event in process.mutex_lock_events:
        assert(event.arrival not in event_arrivals)
        event_arrivals.add(event.arrival)
    
    for event in process.mutex_unlock_events:
        assert(event.arrival not in event_arrivals)
        event_arrivals.add(event.arrival)
    
    for event in process.memory_events:
        assert(event.arrival not in event_arrivals)
        event_arrivals.add(event.arrival)

    for event_arrival in event_arrivals:
        assert(event_arrival < process.total_cpu_time)

def print_usage():
    print("Usage: python simulator.py <simulation_description_path> <log_path> <optional --no-student-logs>")
    sys.exit(1)


if __name__ == "__main__":
    student_logs = True
    if len(sys.argv) <= 2 or len(sys.argv) >= 5:
        print_usage()
    if type(sys.argv[1]) is not str or type(sys.argv[2]) is not str:
        print_usage()
    if len(sys.argv) == 4:
        if sys.argv[3] != "--no-student-logs":
            print_usage()
        else:
            student_logs = False



    sim_description = Path(sys.argv[1])
    log_path = Path(sys.argv[2])
    simulator = Simulator(sim_description, log_path, student_logs)
    simulator.run_simulator()