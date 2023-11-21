
from resources.workload import Workload 
from resources.node.Node import Node 

class NodeTaintConstraint: 
    
	def add_workload_constraints(self): 
		for taint in self.node.taints:
			for workload_idx in range(len(self.workload_assignments_for_node)):
				wl = self.workloads[workload_idx]
				if taint.can_workload_tolerate_taint(wl) == False:
					self.model.addConstr(self.workload_assignments_for_node[workload_idx] == 0) 

	def __init__(self, m, node: list[Node], workloads: list[Workload], workload_assignments_for_node): 
		self.model = m 
		self.node = node 
		self.workloads = workloads 
		self.workload_assignments_for_node = workload_assignments_for_node 

		self.add_workload_constraints()

