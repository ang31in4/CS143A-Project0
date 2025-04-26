from io import TextIOWrapper
import json
from dataclasses import dataclass
from pathlib import Path
import sys

from kernel import Kernel

MICRO_S = int
PID = int

NUM_MICRO_IN_SEC: MICRO_S = 1000000

VALID_SCHEDULING_ALGORITHMS = {"FCFS", "Priority"}

PROCESSES: str = "processes"
ARRIVAL: str = "arrival"
TOTAL_CPU_TIME: str = "total_cpu_time"
PRIORITY: str = "priority"
PRIORITY_CHANGES: str = "priority_change"
EVENT_ARRIVAL: str = "arrival"
NEW_PRIORITY: str = "new_priority"

DEFAULT_PRIORITY = 32

class SimulationError(Exception):
    pass

@dataclass
class PriorityChangeEvent:
    arrival: MICRO_S
    new_priority: int

@dataclass
class Process:
    arrival: MICRO_S
    total_cpu_time: MICRO_S
    elapsed_cpu_time: MICRO_S
    priority: int
    priority_change_events: list[PriorityChangeEvent]


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

    def __init__(self, emulation_description_path: Path, logfile_path: str):
        self.elapsed_time = 0
        self.current_process = 0
        self.processes = dict()
        self.arrivals = []
        self.next_pid = 1
        self.needs_spacing = False
        self.process_0_runtime = 0

        emulation_json = None
        with open(emulation_description_path, 'r') as file:
            emulation_json = json.load(file)

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
            priority_changes.sort(key=lambda c: c.arrival, reverse=True)

            process = Process(process[ARRIVAL], process[TOTAL_CPU_TIME], 0, priority, priority_changes)
            assert_events_are_not_at_same_time(process)
            self.arrivals.append(process)
        # Sort arrivals so earliest arrivals are at the end.
        self.arrivals.sort(key=lambda p: p.arrival, reverse=True)

        assert("scheduling_algorithm" in emulation_json and emulation_json["scheduling_algorithm"] in VALID_SCHEDULING_ALGORITHMS)
        self.kernel = Kernel(emulation_json["scheduling_algorithm"])

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

            # if self.elapsed_time != 0 and self.elapsed_time % TIMER_INTERRUPT_INTERVAL == 0:
            #     self.switch_process(self.handler.timer_interrupt())

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
            exiting_process = self.current_process
            self.log(f"Process {exiting_process} has finished execution and is exiting")
            new_process = self.kernel.syscall_exit()
            if new_process == exiting_process:
                raise SimulationError(f"Attempted to continue execution of exiting process (pid = {exiting_process})")
            
            del self.processes[exiting_process]
            
            self.switch_process(new_process)
            return
        
        while len(current_process.priority_change_events) > 0 and current_process.priority_change_events[len(current_process.priority_change_events) - 1].arrival <= current_process.elapsed_cpu_time:
            priority_change = current_process.priority_change_events.pop()
            self.log(f"Process {self.current_process} set priority to {priority_change.new_priority}")
            self.switch_process(self.kernel.syscall_set_priority(priority_change.new_priority))

    def check_for_arrival(self):
        while len(self.arrivals) > 0 and self.arrivals[len(self.arrivals) - 1].arrival == self.elapsed_time:
            new_process = self.arrivals.pop()
            self.processes[self.next_pid] = new_process
            self.log(f"Process {self.next_pid} arrived with priority {new_process.priority}")
            self.switch_process(self.kernel.new_process_arrived(self.next_pid, new_process.priority))
            self.next_pid += 1


    def switch_process(self, new_process: int):
        if new_process != 0:
            if new_process not in self.processes:
                raise SimulationError(f"Attempted to switch to unkown PID {new_process}")
            self.process_0_runtime = 0

        if new_process != self.current_process:
            self.log(f"Context switching to pid: {new_process}")
        self.current_process = new_process

    def log(self, str):
        self.simlog.write(f"{self.elapsed_time / 1000:.3f}ms : {str}\n")
        self.needs_spacing = True
    
    def log_add_spacing(self):
        if self.needs_spacing:
            self.simlog.write("\n")
            self.needs_spacing = False

# Having events at the same time as other events in the same process could cause a desync between what the simulator thinks is running and what the handler does.
# This assert ensures the process does not have this issue.
def assert_events_are_not_at_same_time(process: Process):
    event_arrivals = set()
    for event in process.priority_change_events:
        assert(event.arrival not in event_arrivals)
        event_arrivals.add(event.arrival)

def print_usage():
    print("Usage: python simulator.py <simulation_description_path> <log_path>")
    sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) != 3 or type(sys.argv[1]) is not str or type(sys.argv[2]) is not str:
        print_usage()


    sim_description = Path(sys.argv[1])
    log_path = Path(sys.argv[2])
    simulator = Simulator(sim_description, log_path)
    simulator.run_simulator()