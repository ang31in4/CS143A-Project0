### Fill in the following information before submitting
# Group id: 37
# Members: Angelina Chau, Daniel Khalkhali, Greg Valijan



from collections import deque

# PID is just an integer, but it is used to make it clear when a integer is expected to be a valid PID.
PID = int

# This class represents the PCB of processes.
# It is only here for your convinience and can be modified however you see fit.
class PCB:
    pid: PID
    priority: int

    def __init__(self, pid: PID, priority: int = 0):
        self.pid = pid
        self.priority = priority


class Logger:
    def log(self, message: str) :
        print(message)


# This class represents the Kernel of the simulation.
# The simulator will create an instance of this object and use it to respond to syscalls and interrupts.
# DO NOT modify the name of this class or remove it.
class Kernel:
    scheduling_algorithm: str
    ready_queue: deque[PCB]
    waiting_queue: deque[PCB]
    running: PCB
    idle_pcb: PCB
    logger: Logger

    # Called before the simulation begins.
    # Use this method to initilize any variables you need throughout the simulation.
    # DO NOT rename or delete this method. DO NOT change its arguments.
    def __init__(self, scheduling_algorithm: str, logger) :
        self.scheduling_algorithm = scheduling_algorithm
        self.ready_queue = deque()
        self.waiting_queue = deque()
        self.idle_pcb = PCB(0)
        self.running = self.idle_pcb
        self.logger = logger
        self.time = 0

    # This method is triggered every time a new process has arrived.
    # new_process is this process's PID.
    # priority is the priority of new_process.
    # DO NOT rename or delete this method. DO NOT change its arguments.
    def new_process_arrived(self, new_process: PID, priority: int, process_type: str) -> PID:
        self.logger.log(f"Ready queue len:{len(self.ready_queue)} when process {new_process} arrived")
        self.ready_queue.append(PCB(new_process, priority, process_type))

        # For FCFS and Priority, immediately choose new process
        # For RR, only choose new process if idle
        if self.scheduling_algorithm != "RR" or self.running == self.idle_pcb:
            return self.choose_next_process().pid
        else:
            return self.running.pid


    # This method is triggered every time the current process performs an exit syscall.
    # DO NOT rename or delete this method. DO NOT change its arguments.
    def syscall_exit(self) -> PID:
        self.running = self.idle_pcb
        return self.choose_next_process().pid


    # This method is triggered when the currently running process requests to change its priority.
    # DO NOT rename or delete this method. DO NOT change its arguments.
    def syscall_set_priority(self, new_priority: int) -> PID:
        self.running.priority = new_priority
        return self.choose_next_process().pid


    # This is where you can select the next process to run.
    # This method is not directly called by the simulator and is purely for your convinience.
    # Feel free to modify this method as you see fit.
    # It is not required to actually use this method but it is recommended.
    def choose_next_process(self):
            
        if self.scheduling_algorithm != "RR" and self.running != self.idle_pcb:                    # For FCFS and Priority, if running process is not idle_pcb, append it to front of queue
            self.ready_queue.appendleft(self.running)
            
        if len(self.ready_queue) == 0:               # if the ready queue is still empty, that means there is no process running or waiting -> idle
            return self.idle_pcb

        if self.scheduling_algorithm == "FCFS":      # Set running process to first in queue if FCFS
            self.running = self.ready_queue.popleft()
        elif self.scheduling_algorithm == "Priority":                                        # If Priority, find best process choice in queue and set it to running process
            best_process = min(self.ready_queue, key=lambda p: (p.priority, p.pid))
            self.ready_queue.remove(best_process)
            self.running = best_process
        elif self.scheduling_algorithm == "RR":     # If RR, choose process in front of queue and reset time
            self.running = self.ready_queue.popleft()
            self.time = 0


        return self.running                          # return new running process

    # This method is triggered when the currently running process requests to initialize a new semaphore.
    # DO NOT rename or delete this method. DO NOT change its arguments.
    def syscall_init_semaphore(self, semaphore_id: int, initial_value: int):
        return
        
    # This method is triggered when the currently running process calls p() on an existing semaphore.
    # DO NOT rename or delete this method. DO NOT change its arguments.
    def syscall_semaphore_p(self, semaphore_id: int) -> PID:
        return self.running.pid

    # This method is triggered when the currently running process calls v() on an existing semaphore.
    # DO NOT rename or delete this method. DO NOT change its arguments.
    def syscall_semaphore_v(self, semaphore_id: int) -> PID:
        return self.running.pid

    # This method is triggered when the currently running process requests to initialize a new mutex.
    # DO NOT rename or delete this method. DO NOT change its arguments.
    def syscall_init_mutex(self, mutex_id: int):
        return

    # This method is triggered when the currently running process calls lock() on an existing mutex.
    # DO NOT rename or delete this method. DO NOT change its arguments.
    def syscall_mutex_lock(self, mutex_id: int) -> PID:
        return self.running.pid


    # This method is triggered when the currently running process calls unlock() on an existing mutex.
    # DO NOT rename or delete this method. DO NOT change its arguments.
    def syscall_mutex_unlock(self, mutex_id: int) -> PID:
        return self.running.pid

    # This function represents the hardware timer interrupt.
    # It is triggered every 10 microseconds and is the only way a kernel can track passing time.
    # Do not use real time to track how much time has passed as time is simulated.
    # DO NOT rename or delete this method. DO NOT change its arguments.
    def timer_interrupt(self) -> PID:
        # Only use timer in RR
        if self.scheduling_algorithm == "RR" and self.running != self.idle_pcb:
            self.time += 1  # Increment for every 10 microseconds

        # Switch process if 40 microseconds have passed
        if self.time >= 4:
            if self.running != self.idle_pcb:
                self.ready_queue.append(self.running)   # Put current process at end of queue
            return self.choose_next_process().pid

        return self.running.pid