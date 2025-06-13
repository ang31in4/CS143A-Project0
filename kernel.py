### Fill in the following information before submitting
# Group id: 37
# Members: Angelina Chau, Daniel Khalkhali, Greg Valijan


from collections import deque
from dataclasses import dataclass

# PID is just an integer, but it is used to make it clear when a integer is expected to be a valid PID.
PID = int

BACKGROUND: str = "Background"
FOREGROUND: str = "Foreground"

# This class represents the PCB of processes.
# It is only here for your convinience and can be modified however you see fit.
class PCB:
    pid: PID
    priority: int
    num_quantum_ticks: int
    process_type: str
    memory_needed: int

    def __init__(self, pid: PID, priority: int, process_type: str, memory_needed: int):
        self.pid = pid
        self.priority = priority
        self.num_quantum_ticks = 0
        self.process_type = process_type
        self.memory_needed = memory_needed

    def __str__(self):
        return f"({self.pid}, {self.priority})"
    
    def __repr__(self):
        return f"({self.pid}, {self.priority})"

@dataclass
class Semaphore:
    value: int
    waiting: deque[PCB]

class Mutex:
    semaphore: Semaphore

    def __init__(self):
        # A mutex is essentially a semaphore with a value of 1
        self.semaphore = Semaphore(1, deque())

RR_QUANTUM_TICKS: int = 4
ACTIVE_QUEUE_NUM_TICKS: int = 20

MULTILEVEL: str = "Multilevel"
RR: str = "RR"
FCFS: str = "FCFS"
PRIORITY: str = "Priority"

# This class represents the Kernel of the simulation.
# The simulator will create an instance of this object and use it to respond to syscalls and interrupts.
# DO NOT modify the name of this class or remove it.
class Kernel:
    scheduling_algorithm: str
    ready_queue: deque[PCB]
    waiting_queue: deque[PCB]
    running: PCB
    idle_pcb: PCB
    semaphores: dict[int, Semaphore]
    mutexes: dict[int, Mutex]
    fcfs_ready_queue: deque[PCB]
    rr_ready_queue: deque[PCB]
    active_queue: str
    active_queue_num_ticks: int
    mmu: "MMU"
    memory_size: int

    # Called before the simulation begins.
    # Use this function to initilize any variables you need throughout the simulation.
    # DO NOT rename or delete this method. DO NOT change its arguments.
    def __init__(self, scheduling_algorithm: str, logger, mmu: "MMU", memory_size: int):
        self.scheduling_algorithm = scheduling_algorithm
        self.ready_queue = deque()
        self.waiting_queue = deque()
        self.idle_pcb = PCB(0, 0, "Foreground", 0)
        self.running = self.idle_pcb
        self.semaphores = dict()
        self.mutexes = dict()
        self.logger = logger
        self.fcfs_ready_queue = deque()
        self.rr_ready_queue = deque()
        self.active_queue = FOREGROUND
        self.active_queue_num_ticks = 0
        self.mmu = mmu
        self.memory_size = memory_size
        self.mmu.define_memory(memory_size)

    # This function is triggered every time a new process has arrived.
    # new_process is this process's PID.
    # priority is the priority of new_process.
    # DO NOT rename or delete this method. DO NOT change its arguments.
    def new_process_arrived(self, new_process: PID, priority: int, process_type: str, memory_needed: int) -> PID:
        if self.mmu.allocate_memory(memory_needed, new_process) == -1:
            return -1
        
        self.ready_queue.append(PCB(new_process, priority, process_type, memory_needed))

        # Neither queue was active, so when a process arrives, it is the start of a new queue
        if self.scheduling_algorithm == MULTILEVEL and self.running is self.idle_pcb:
            self.active_queue_num_ticks = 0
        
        self.choose_next_process()
        return self.running.pid  

    # This function is triggered every time the current process performs an exit syscall.
    # DO NOT rename or delete this method. DO NOT change its arguments.
    def syscall_exit(self) -> PID:
        self.mmu.free_memory(self.running.pid)
        self.running = self.idle_pcb
        self.choose_next_process()
        return self.running.pid
    
    # This function is triggered when the currently running process requests to change its priority.
    # DO NOT rename or delete this method. DO NOT change its arguments.
    def syscall_set_priority(self, new_priority: int) -> PID:
        self.running.priority = new_priority
        self.choose_next_process()
        return self.running.pid


    # This is where you can select the next process to run.
    # This function is not directly called by the simulator and is purely for your convinience.
    # It is not required to actually use this function but it is recommended.
    def choose_next_process(self):
        if self.scheduling_algorithm == FCFS:
            self.fcfs_chose_next_process(self.ready_queue)
        elif self.scheduling_algorithm == PRIORITY:
            if len(self.ready_queue) == 0:
                return
            
            if self.running is not self.idle_pcb:
                self.ready_queue.append(self.running)

            next_process = pop_min_priority(self.ready_queue)
            self.running = next_process
        elif self.scheduling_algorithm == RR:
            self.rr_chose_next_process(self.ready_queue)
        elif self.scheduling_algorithm == MULTILEVEL:
            # Move everything in standard ready queue to proper queues
            while len(self.ready_queue) > 0:
                pcb = self.ready_queue.popleft()
                if pcb.process_type == FOREGROUND:
                    self.rr_ready_queue.append(pcb)
                elif pcb.process_type == BACKGROUND:
                    self.fcfs_ready_queue.append(pcb)
                else:
                    print("Unknown process type")
            
            if self.active_queue == FOREGROUND:
                # RR queue
                self.rr_chose_next_process(self.rr_ready_queue)
            elif self.active_queue == BACKGROUND:
                # FCFS queue
                self.fcfs_chose_next_process(self.fcfs_ready_queue)
                   
            # If we have nothing to run in the current queue switch the queue
            if self.running is self.idle_pcb:
                self.switch_active_queue()
                if self.active_queue == FOREGROUND:
                    # RR queue
                    self.rr_chose_next_process(self.rr_ready_queue)
                elif self.active_queue == BACKGROUND:
                    # FCFS queue
                    self.fcfs_chose_next_process(self.fcfs_ready_queue)
            
        else:
            print("Unknown scheduling algorithm")

    def rr_chose_next_process(self, queue: deque[PCB]):
        if self.running is self.idle_pcb:
            if len(queue) == 0:
                return
        
            self.running = queue.popleft()
        elif exceeded_quantum(self.running):
            # Put on end of queue and run next process
            queue.append(self.running)
            self.running = queue.popleft()

    def fcfs_chose_next_process(self, queue: deque[PCB]):
        if len(queue) == 0:
            return
        
        if self.running is self.idle_pcb:
            # Lower pid was the first to arrive
            self.running = pop_min_pid(queue)

    def switch_active_queue(self):
        # Reset the number of ticks with the active queue
        self.active_queue_num_ticks = 0

        if self.active_queue == FOREGROUND:
            # If background has no processes do nothing.
            if len(self.fcfs_ready_queue) == 0:
                return
            
            if self.running is not self.idle_pcb:
                # If the running process should be switched out, move it to the back before switching
                if exceeded_quantum(self.running):
                    self.rr_ready_queue.append(self.running)
                    self.running = self.idle_pcb
                # If the running process should not be switched out, make it run first when we switch back
                else:
                    self.rr_ready_queue.appendleft(self.running)
                    self.running = self.idle_pcb

            self.active_queue = BACKGROUND
        elif self.active_queue == BACKGROUND:
            # If foreground has no processes do nothing.
            if len(self.rr_ready_queue) == 0:
                return

            if self.running is not self.idle_pcb:
                self.fcfs_ready_queue.appendleft(self.running)
                self.running = self.idle_pcb
            self.active_queue = FOREGROUND
        else:
            print("Unknown active queue")

    def semaphore_p(self, semaphore: Semaphore):
        if semaphore.value <= 0:
            semaphore.waiting.append(self.running)
            self.running = self.idle_pcb
            self.choose_next_process()
        else:
            semaphore.value -= 1

    def semaphore_v(self, semaphore: Semaphore):
        if semaphore.value <= 0 and len(semaphore.waiting) > 0:
            to_be_released = None

            if self.scheduling_algorithm == PRIORITY:
                to_be_released = pop_min_priority(semaphore.waiting)
            else:
                to_be_released = pop_min_pid(semaphore.waiting)

            self.ready_queue.append(to_be_released)
            to_be_released.num_quantum_ticks = 0
            self.choose_next_process()
            # Don't increment value because we freed a process instead
        else: 
            semaphore.value += 1

    # This method is triggered when the currently running process requests to initilize a new semaphore.
    # DO NOT rename or delete this method. DO NOT change its arguments.
    def syscall_init_semaphore(self, semaphore_id: int, initial_value: int):
        self.semaphores[semaphore_id] = Semaphore(initial_value, deque())
    
    # This method is triggered when the currently running process calls p() on an existing semaphore.
    # DO NOT rename or delete this method. DO NOT change its arguments.
    def syscall_semaphore_p(self, semaphore_id: int) -> PID:
        self.semaphore_p(self.semaphores[semaphore_id])
        return self.running.pid 

    # This method is triggered when the currently running process calls v() on an existing semaphore.
    # DO NOT rename or delete this method. DO NOT change its arguments.
    def syscall_semaphore_v(self, semaphore_id: int) -> PID:
        self.semaphore_v(self.semaphores[semaphore_id])
        return self.running.pid 

    # This method is triggered when the currently running process requests to initilize a new mutex.
    # DO NOT rename or delete this method. DO NOT change its arguments.
    def syscall_init_mutex(self, mutex_id: int):
        self.mutexes[mutex_id] = Mutex()

    # This method is triggered when the currently running process calls lock() on an existing mutex.
    # DO NOT rename or delete this method. DO NOT change its arguments.
    def syscall_mutex_lock(self, mutex_id: int) -> PID:
        self.semaphore_p(self.mutexes[mutex_id].semaphore)
        return self.running.pid 


    # This method is triggered when the currently running process calls unlock() on an existing mutex.
    # DO NOT rename or delete this method. DO NOT change its arguments.
    def syscall_mutex_unlock(self, mutex_id: int) -> PID:
        self.semaphore_v(self.mutexes[mutex_id].semaphore)
        return self.running.pid 

    # This function represents the hardware timer intterupt.
    # It is triggered every 10 microseconds and is the only way a kernel can track passing time.
    # Do not use real time to track how much time has passed as time is simulated.
    def timer_interrupt(self) -> PID:
        self.running.num_quantum_ticks += 1
        self.active_queue_num_ticks += 1

        if self.scheduling_algorithm == RR:
            self.choose_next_process()
        elif self.scheduling_algorithm == MULTILEVEL:
            if self.active_queue_num_ticks >= ACTIVE_QUEUE_NUM_TICKS:
                self.switch_active_queue()
            self.choose_next_process()
        return self.running.pid 
    
# This class represents the MMU of the simulation.
# The simulator will create an instance of this object and use it to translate memory accesses.
# DO NOT modify the name of this class or remove it.
class MMU:
    VIRTUAL_BASE = 0x20000000

    memory_size: int
    # Called before the simulation begins (even before kernel __init__).
    # Use this function to initilize any variables you need throughout the simulation.
    # DO NOT rename or delete this method. DO NOT change its arguments.
    def __init__(self, logger):
        self.logger = logger

    def define_memory(self, memory_size: int):
        self.memory = [(10485760, memory_size, None)]

    # Translate the virtual address to its physical address.
    # If it is not a valid address for the given process, return None which will cause a segmentation fault.
    # DO NOT rename or delete this method. DO NOT change its arguments.
    def translate(self, address: int, pid: PID) -> int | None:
        # Locate the process's memory block
        for start, end, id in self.memory:
            # self.logger.log(f"Searching for {pid}: start: 0x{start:0x} end: 0x{end+1:0x} id: {id}\n")
            if id == pid:
                # self.logger.log(f"found allocation\n")
                # Translate virtual to physical address
                physical_address = address - self.VIRTUAL_BASE + start
                # self.logger.log(f"vir add: 0x{address:0x} phys address 0x{physical_address:0x}\n")

                # Check if the physical address is within bounds
                if start <= physical_address <= end:
                    # self.logger.log(f"in bounds\n")
                    return physical_address
                else:
                    return None
        return None

    # Allocate a part of the memory (passed by the kernel) to the process with id: process_id
    # Returns -1 if not enough space, otherwise returns pid
    def allocate_memory(self, size:int, pid: PID):
        best_fit_index = -1
        best_fit_size = float('inf')

        # Find the smallest free block that can accommodate the size
        for i, (start, end, id) in enumerate(self.memory):
            if id is None:  # Free block
                block_size = end - start + 1
                if block_size >= size and block_size < best_fit_size:
                    best_fit_size = block_size
                    best_fit_index = i

        if best_fit_index == -1:
            return -1  # No suitable block found

        # Allocate memory in the best-fit block
        start, end, _ = self.memory[best_fit_index]
        allocated_block = (start, start + size - 1, pid)
        remaining_block = (start + size, end, None) if start + size <= end else None

        self.memory[best_fit_index] = allocated_block
        if remaining_block:
            self.memory.insert(best_fit_index + 1, remaining_block)

        return pid

    # Deallocate the part of memory used by given process
    # Combine holes in memory
    # Returns -1 if process was not found and pid if successful
    def free_memory(self, pid):
        for i, (start, end, id) in enumerate(self.memory):
            if pid == id:
                self.memory[i] = (start, end, None)  # Mark as a hole
                
                # Merge adjacent free blocks
                if i > 0 and self.memory[i - 1][2] is None:
                    self.memory[i - 1] = (self.memory[i - 1][0], end, None)
                    del self.memory[i]
                    i -= 1  # Adjust index after deletion

                # Merge with the next block if free
                if i < len(self.memory) - 1 and self.memory[i + 1][2] is None:
                    self.memory[i] = (self.memory[i][0], self.memory[i + 1][1], None)
                    del self.memory[i + 1]

                return pid  # Deallocation successful
            
        return -1  # Process not found

def exceeded_quantum(pcb: PCB) -> bool:
    if pcb.num_quantum_ticks >= RR_QUANTUM_TICKS:
        pcb.num_quantum_ticks = 0
        return True
    else:
        return False
    
def pop_min_priority(pcbs: list[PCB]) -> PCB:
    min_index = 0
    for i in range(1, len(pcbs)):
        process = pcbs[i]
        if process.priority < pcbs[min_index].priority:
            min_index = i
        elif process.priority == pcbs[min_index].priority and process.pid < pcbs[min_index].pid:
            min_index = i
    popped = pcbs[min_index]
    del pcbs[min_index]
    return popped

def pop_min_pid(pcbs: list[PCB]):
    lowest_pid_i = 0
    for i in range(1, len(pcbs)):
        if pcbs[i].pid < pcbs[lowest_pid_i].pid:
            lowest_pid_i = i
    popped = pcbs[lowest_pid_i]
    del pcbs[lowest_pid_i]
    return popped