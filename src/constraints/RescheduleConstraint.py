
from resources.workload import Workload
from resources.node.Node import Node  
from resources.WorkloadAssignment import WorkloadAssignment 

class RescheduleConstraint: 
	
	def setup_reschedule_vars(self):  
		reschedule_vars = []
		for workload_index in range(len(self.workloads)): 
			workload = self.workloads[workload_index] 

			reschedule_var = self.model.addVar(vtype='B', name=workload.name+"-has-to-be-rescheduled") 
			reschedule_vars.append(reschedule_var)
			for node_index in range(len(self.nodes)): 
				node = self.nodes[node_index] 

				assignment_var = self.workload_assignment.get(workload_index, node_index) 

				if(node.name == workload.current_node_name): 
					self.model.addConstr((assignment_var == 1) >> (reschedule_var == 0))
				else: 
					self.model.addConstr((assignment_var == 1) >> (reschedule_var == 1)) 
		
		return reschedule_vars 
	

	def __init__(self, model, workloads : list[Workload], nodes: list[Node], workload_assignment: WorkloadAssignment): 
		self.model = model  
		self.workloads = workloads   
		self.nodes = nodes  
		self.workload_assignment = workload_assignment 

		self.reschedule_vars = self.setup_reschedule_vars()
	

