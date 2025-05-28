### Fill in the following information before submitting
# Group id: 37
# Members: Angelina Chau, Daniel Khalkhali, Greg Valijan



from collections import deque

# PID is just an integer, but it is used to make it clear when a integer is expected to be a valid PID.
PID = int

# This class represents the PCB of processes.
# It is only here for your convinience and can be modified however you see fit.
class PCB:
    # pid: PID
    # priority: int

    def __init__(self, pid: PID, priority: int = 0):
        self.pid = pid
        self.priority = priority


# This class represents the Kernel of the simulation.
# The simulator will create an instance of this object and use it to respond to syscalls and interrupts.
# DO NOT modify the name of this class or remove it.
class Kernel:
    # scheduling_algorithm: str
    # ready_queue: deque[PCB]
    # foreground_queue: deque[PCB]
    # background_queue: deque[PCB]
    # running: PCB
    # idle_pcb: PCB

    # Called before the simulation begins.
    # Use this method to initilize any variables you need throughout the simulation.
    # DO NOT rename or delete this method. DO NOT change its arguments.
    def __init__(self, scheduling_algorithm: str, logger) :
        self.scheduling_algorithm = scheduling_algorithm
        self.ready_queue = deque()
        self.foreground_queue = deque()
        self.background_queue = deque()
        self.state = "Foreground"
        self.wait = 0
        self.idle_pcb = PCB(0)
        self.running = self.idle_pcb
        self.logger = logger
        self.time_quants = 0
        self.time_context = 0
        self.semaphores = {}
        self.mutexes = {}

    # This method is triggered every time a new process has arrived.
    # new_process is this process's PID.
    # priority is the priority of new_process.
    # DO NOT rename or delete this method. DO NOT change its arguments.
    # def new_process_arrived(self, new_process: PID, priority: int, process_type: str) -> PID:
    #     # self.logger.log(f"Ready queue length {len(self.ready_queue)} when process {new_process} arrived")
    #     if(self.scheduling_algorithm == "Multilevel"):
    #         if(process_type == "Foreground"):
    #             self.foreground_queue.append(PCB(new_process, priority))
    #         else:
    #             self.background_queue.append(PCB(new_process, priority))
    #     else:
    #         self.ready_queue.append(PCB(new_process, priority))

    #     if self.running is self.idle_pcb or self.scheduling_algorithm != "RR":
    #         self.choose_next_process()
            
    #     return self.running.pid

    def new_process_arrived(self, new_process: PID, priority: int, process_type: str) -> PID:
        if(self.scheduling_algorithm == "Multilevel"):
            if(process_type == "Foreground"):
                #self.logger.log(f"Foreground queue len: {len(self.foreground_queue)} when process {new_process} arrived")
                # if len(self.foreground_queue) == 0:
                #     self.time_context = 0
                self.foreground_queue.append(PCB(new_process, priority))
                self.wait = 1
            else:
                # self.logger.log(f"Background queue len: {len(self.background_queue)} when process {new_process} arrived")
                # if len(self.background_queue) == 0:
                #     self.time_context = 0
                self.background_queue.append(PCB(new_process, priority))
        else:
            #self.logger.log(f"Ready queue len: {len(self.ready_queue)} when process {new_process} arrived")
            self.ready_queue.append(PCB(new_process, priority))

        # For FCFS and Priority, immediately choose new process
        # For RR, only choose new process if idle
        if (self.scheduling_algorithm == "FCFS" 
            or self.scheduling_algorithm == "Priority" 
            or self.state == "Background" 
            or self.running == self.idle_pcb):
            return self.choose_next_process().pid
        else:
            return self.running.pid

    # This method is triggered every time the current process performs an exit syscall.
    # DO NOT rename or delete this method. DO NOT change its arguments.
    def syscall_exit(self) -> PID:
        self.running = self.idle_pcb
        if self.scheduling_algorithm == "Multilevel":
            if self.state == "Foreground":
                if len(self.foreground_queue) == 0 and self.running is self.idle_pcb:    # if the ready queue is still empty, that means there is no process running or waiting -> idle
                    if len(self.background_queue) == 0:
                        return self.idle_pcb.pid
                    else:
                        self.state = "Background"
                        self.time_context = 0
                        self.running = self.background_queue.popleft()
                else:
                    self.running = self.foreground_queue.popleft()
                    self.time_quants = 0
            elif self.state == "Background":
                if len(self.background_queue) == 0 and self.running is self.idle_pcb:
                    if len(self.foreground_queue) == 0:
                        return self.idle_pcb.pid
                    else:
                        self.state = "Foreground"
                        self.time_context = 0
                        self.running = self.foreground_queue.popleft()
                else:
                    if self.running is self.idle_pcb:
                        self.running = self.background_queue.popleft()
        else:
            self.running = self.choose_next_process()
        return self.running.pid


    # This method is triggered when the currently running process requests to change its priority.
    # DO NOT rename or delete this method. DO NOT change its arguments.
    def syscall_set_priority(self, new_priority: int) -> PID:
        self.running.priority = new_priority
        self.choose_next_process()
        return self.running.pid


    # This is where you can select the next process to run.
    # This method is not directly called by the simulator and is purely for your convinience.
    # Feel free to modify this method as you see fit.
    # It is not required to actually use this method but it is recommended.
    def choose_next_process(self):
        #self.logger.log(f"Currently running: {self.running.pid} {self.state}, time: {self.time_quants}, context: {self.time_context}")
        if self.scheduling_algorithm == "Multilevel":
            if self.state == "Foreground":
                if len(self.foreground_queue) == 0 and self.running is self.idle_pcb:    # if the ready queue is still empty, that means there is no process running or waiting -> idle
                    if len(self.background_queue) == 0:
                        return self.idle_pcb
                    else:
                        self.state = "Background"
                        #self.time_quants = 0
                        self.time_context = 0
                        self.running = self.background_queue.popleft()
                else:
                    self.running = self.foreground_queue.popleft()
            elif self.state == "Background":
                if len(self.background_queue) == 0 and self.running is self.idle_pcb:
                    if len(self.foreground_queue) == 0:
                        return self.idle_pcb
                    else:
                        self.state = "Foreground"
                        #self.time_quants = 0
                        self.time_context = 0
                        self.running = self.foreground_queue.popleft()
                else:
                    if self.running is self.idle_pcb:
                        self.running = self.background_queue.popleft()

        else:
            # if self.scheduling_algorithm != "RR" and self.running != self.idle_pcb:    # For FCFS and Priority, if running process is not idle_pcb, append it to front of queue
            #     self.ready_queue.appendleft(self.running)

            # if len(self.ready_queue) == 0:               # if the ready queue is still empty, that means there is no process running or waiting -> idle
            #     return self.idle_pcb

            # if self.scheduling_algorithm == "FCFS":      # Set running process to first in queue if FCFS
            #     self.running = self.ready_queue.popleft()

            # elif self.scheduling_algorithm == "Priority":                                        # If Priority, find best process choice in queue and set it to running process
            #     best_process = min(self.ready_queue, key=lambda p: (p.priority, p.pid))
            #     self.ready_queue.remove(best_process)
            #     self.running = best_process
                
            # elif self.scheduling_algorithm == "RR":     # If RR, choose process in front of queue and reset time
            #     self.running = self.ready_queue.popleft()
            #     self.time_quants = 0

            #     if self.scheduling_algorithm != "RR" and self.running != self.idle_pcb:                    # For FCFS and Priority, if running process is not idle_pcb, append it to front of queue
            # self.ready_queue.appendleft(self.running)

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
                self.time_quants = 0
                
        return self.running                          # return new running process

    # This method is triggered when the currently running process requests to initialize a new semaphore.
    # DO NOT rename or delete this method. DO NOT change its arguments.
    def syscall_init_semaphore(self, semaphore_id: int, initial_value: int):
        self.semaphores[semaphore_id] = {'count': initial_value, 'waiters': deque()}
        
    # This method is triggered when the currently running process calls p() on an existing semaphore.
    # DO NOT rename or delete this method. DO NOT change its arguments.
    def syscall_semaphore_p(self, semaphore_id: int) -> PID:
        sem = self.semaphores[semaphore_id]
        if sem['count'] > 0:
            sem['count'] -= 1
            return self.running.pid

        # --- block path ---
        sem['waiters'].append(self.running)
        self.running = self.idle_pcb
        return self.choose_next_process().pid


    # This method is triggered when the currently running process calls v() on an existing semaphore.
    # DO NOT rename or delete this method. DO NOT change its arguments
    def syscall_semaphore_v(self, semaphore_id: int) -> PID:
        sem = self.semaphores[semaphore_id]

        if sem['waiters']:
            # pick one waiter by priority or PID
            if self.scheduling_algorithm == "Priority":
                to_wake = min(sem['waiters'], key=lambda p: (p.priority, p.pid))
            else:
                to_wake = min(sem['waiters'], key=lambda p: p.pid)
            sem['waiters'].remove(to_wake)

            if self.scheduling_algorithm == "FCFS":
                # non-preemptive
                self.ready_queue.append(to_wake)
                return self.running.pid

            elif self.scheduling_algorithm == "Priority":
                # Only preempt if the newly unblocked process has higher priority
                if to_wake.priority < self.running.priority:
                    if self.running != self.idle_pcb:
                        self.ready_queue.append(self.running)
                    self.running = to_wake
                    return self.running.pid
                else:
                    self.ready_queue.append(to_wake)
                    return self.running.pid

            elif self.scheduling_algorithm == "RR":
                self.ready_queue.append(to_wake)

                return self.running.pid
        else:
            # no waiters → bump the count
            sem['count'] += 1
            return self.running.pid


    # This method is triggered when the currently running process requests to initialize a new mutex.
    # DO NOT rename or delete this method. DO NOT change its arguments.
    def syscall_init_mutex(self, mutex_id: int):
        self.mutexes[mutex_id] = {'locked': False,'owner':  None,'waiters': deque()}

    # This method is triggered when the currently running process calls lock() on an existing mutex.
    # DO NOT rename or delete this method. DO NOT change its arguments.
    def syscall_mutex_lock(self, mutex_id: int) -> PID:
        m = self.mutexes[mutex_id]
        if not m['locked']:
            m['locked'] = True
            m['owner']  = self.running.pid
            return self.running.pid
        # --- block path ---
        m['waiters'].append(self.running)
        self.running = self.idle_pcb
        return self.choose_next_process().pid


    # This method is triggered when the currently running process calls unlock() on an existing mutex.
    # DO NOT rename or delete this method. DO NOT change its arguments.
    def syscall_mutex_unlock(self, mutex_id: int) -> PID:
        m = self.mutexes[mutex_id]

        if m['owner'] != self.running.pid:
            return self.running.pid

        if m['waiters']:
            # pick one waiter by priority or PID
            if self.scheduling_algorithm == "Priority":
                to_wake = min(m['waiters'], key=lambda p: (p.priority, p.pid))
            else:
                to_wake = min(m['waiters'], key=lambda p: p.pid)
            m['waiters'].remove(to_wake)

            # transfer lock
            m['owner']  = to_wake.pid
            m['locked'] = True

            if self.scheduling_algorithm == "Priority":
                if to_wake.priority < self.running.priority:
                    if self.running != self.idle_pcb:
                        self.ready_queue.append(self.running)
                    self.running = to_wake
                    return self.running.pid
                else:
                    self.ready_queue.append(to_wake)
                    return self.running.pid

            elif self.scheduling_algorithm == "FCFS":
                self.running = to_wake
                return self.running.pid

            elif self.scheduling_algorithm == "RR":
                self.ready_queue.append(to_wake)
                return self.running.pid
        else:
            # no waiters → simple unlock
            m['locked'] = False
            m['owner']  = None
            return self.running.pid

    # This function represents the hardware timer interrupt.
    # It is triggered every 10 microseconds and is the only way a kernel can track passing time.
    # Do not use real time to track how much time has passed as time is simulated.
    # DO NOT rename or delete this method. DO NOT change its arguments.    
    def timer_interrupt(self) -> PID:
        if self.scheduling_algorithm == "RR":
            if self.running != self.idle_pcb:
                self.time_quants += 1  # Increment for every 10 microseconds

            # Switch process if 40 microseconds have passed
            if self.time_quants >= 4:
                if self.running != self.idle_pcb:
                    self.ready_queue.append(self.running)   # Put current process at end of queue
                self.choose_next_process()

        if self.scheduling_algorithm == "Multilevel":

            if self.running != self.idle_pcb:
                self.time_context += 1
            else:
                self.time_context = 0

            if self.state == "Foreground":
                if self.running != self.idle_pcb:
                    self.time_quants += 1  # Increment for every 10 microseconds

                # Switch process if 40 microseconds have passed
                if self.time_quants >= 4 and self.wait == 0:
                    self.time_quants = 0
                    if self.running != self.idle_pcb:
                        self.foreground_queue.append(self.running)   # Put current process at end of queue
                    self.choose_next_process()
                self.wait = 0

                if self.time_context >= 20:
                    self.time_context = 0
                    if len(self.background_queue) > 0:
                        self.state = "Background"
                        if self.running != self.idle_pcb:
                            self.foreground_queue.appendleft(self.running)
                            self.running = self.idle_pcb
                    else:
                        self.foreground_queue.appendleft(self.running)
                    self.choose_next_process().pid
            
            else:
                if self.time_context >= 20:
                    self.time_context = 0
                    if len(self.foreground_queue) > 0:
                        self.state = "Foreground"
                        if self.running != self.idle_pcb:
                            self.background_queue.appendleft(self.running)   # Put current process at end of queue
                            self.running = self.idle_pcb
                        self.choose_next_process()

        return self.running.pid
        