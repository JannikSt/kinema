import math

from resources.workload import Workload
from resources.WorkloadAssignment import WorkloadAssignment 
from resources.node.Taint import Taint

from resources.NodePool import NodePool

class Node:  
    def prase_taints(self, config: dict): 
         if config is not None and "taints" in config and config["taints"] is not None:  
             return [Taint(t) for t in config["taints"]] 
         else: 
            return [] 

    def __init__(self, config: dict):  
        self.initial_config = config 

        self.name = config["name"]  
        self.pool_name = config["poolname"] 
        self.node_pool : NodePool = config["node_pool"] if config and "node_pool" in config else None 
        self.machine_type = config["machine_type"] if config and "machine_type" in config else None 
        self.allocatable_cpu = config["allocatableCPU"] 
        self.allocatable_memory = config["allocatableMemory"]   
        self.cost_per_hour = config["costPerHour"]  
        self.isVirtual = config["isVirtual"] if config and "isVirtual" in config and type(config["isVirtual"]) == bool else False
        self.taints : list[Taint] = self.prase_taints(config) 

        # print("Node ", self.name, " machine", self.node_pool.provider_machine_name, " memory - ", self.allocatable_memory, " cpu - ", self.allocatable_cpu)
    
    def copy(self): 
        return Node(self.initial_config)

    def calculate_amount_of_node_to_fit_full_workload(self, workloads): 
        memory_request = Workload.get_total_request_for_workloads(workloads, 'memory') 
        cpu_request = Workload.get_total_request_for_workloads(workloads, 'cpu') 

        cpu_count = math.ceil(cpu_request / self.allocatable_cpu) 
        memory_node_count = math.ceil(memory_request / self.allocatable_memory) 

        return max(cpu_count, memory_node_count) 
    
    def get_allocated_memory(self, node_index, workloads: list[Workload], daemon_sets: list[Workload], workload_assignments: WorkloadAssignment, node_usage_var): 
        assignments = workload_assignments.get_workloads_for_node(node_index)  

        if(len(assignments) == 0): 
            return []  
        
        mem_allocation_vars = []

        for a_index in range(len(assignments)):  
            assignment = assignments[a_index]   
            workload = workloads[a_index] 
            mem_allocation_vars.append(assignment * workload.memory_request)
                
        for daemon_set in daemon_sets:  
            mem_allocation_vars.append(node_usage_var * daemon_set.memory_request)
        
        return mem_allocation_vars 

    def get_allocated_cpu(self, node_index, workloads: list[Workload], daemon_sets: list[Workload], workload_assignments: WorkloadAssignment, node_usage_var): 
        assignments = workload_assignments.get_workloads_for_node(node_index)  

        if(len(assignments) == 0): 
            return [] 

        cpu_allocation_vars = [] 

        for a_index in range(len(assignments)):  
            assignment = assignments[a_index]   
            workload = workloads[a_index] 
            cpu_allocation_vars.append(assignment * workload.cpu_request)
                
        for daemon_set in daemon_sets:  
            cpu_allocation_vars.append(assignment * daemon_set.cpu_request ) 
        
        return cpu_allocation_vars

    def get_allocated_resources(self, node_index, workloads: list[Workload], daemon_sets: list[Workload], workload_assignments: WorkloadAssignment, use_start_var): 
        assignments = workload_assignments.get_workloads_for_node(node_index)  

        cpu_allocation = 0 
        mem_allocation = 0

        for a_index in range(len(assignments)):  
            assignment = assignments[a_index]  

            if assignment is not "": 
                is_assigned = assignment.Start == 1 if use_start_var is True else assignment.X == 1

                if is_assigned: 
                    workload = workloads[a_index] 
                    cpu_allocation += workload.cpu_request 
                    mem_allocation += workload.memory_request   
                
        for daemon_set in daemon_sets: 
            cpu_allocation += daemon_set.cpu_request 
            mem_allocation += daemon_set.memory_request   
        
        return cpu_allocation, mem_allocation

    def print_workload_allocation_on_node(self, node_index, workloads: list[Workload], daemon_sets: list[Workload], workload_assignments: WorkloadAssignment): 
        """
        This is only the workload allocation! 
        It does not yet include daemon sets
        """
        cpu_allocation, mem_allocation = self.get_allocated_resources(node_index, workloads, daemon_sets, workload_assignments, False)
        print(self.name+"\t"+str(round(cpu_allocation / self.allocatable_cpu * 100))+"%\t"+str(round(mem_allocation / self.allocatable_memory * 100))+"%") 

     
def ensure_node_names_are_unique(nodes: list[Node]): 
    name_array = [node.name for node in nodes] 
    return len(name_array) == len(set(name_array)) 

def calculate_hour_price_for_node_list(nodes: list[Node]): 
    hour_price = 0 
    for node in nodes:  
        if node.cost_per_hour is not None: 
            hour_price += node.cost_per_hour

    return hour_price  

def calc_resource_utilization(nodes: list[Node], workloads: list[Workload], daemon_sets: list[Workload], workload_assignments: WorkloadAssignment, use_start_var, count_virtual_nodes, node_usage_vars): 
    allocatable_cpu = 0 
    allocatable_memory = 0 
    requested_cpu = 0
    requested_memory = 0

    for node_index in range(len(nodes)): 
       node = nodes[node_index]    
       cpu, memory = node.get_allocated_resources(node_index, workloads, daemon_sets, workload_assignments, use_start_var) 
       if node.isVirtual is False or count_virtual_nodes is True: 
        if(len(node_usage_vars)) == 0 or node_usage_vars[node_index].X == 1: 
            allocatable_cpu += node.allocatable_cpu 
            allocatable_memory += node.allocatable_memory 
            requested_cpu += cpu 
            requested_memory += memory 

    return allocatable_cpu, allocatable_memory, requested_cpu, requested_memory
