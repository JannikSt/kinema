

from resources.workload import Workload 
from resources.node.Node import Node 

class NodeSelectorConstraint: 
    
	def add_node_selector_constraint(self): 
		for workload_idx in range(len(self.workload_assignments_for_node)):
			wl = self.workloads[workload_idx]  
			
			if wl.node_selector and wl.node_selector != self.node.pool_name:
				self.model.addConstr(self.workload_assignments_for_node[workload_idx] == 0)  

	def __init__(self, m, node: list[Node], workloads: list[Workload], workload_assignments_for_node): 
		self.model = m 
		self.node = node 
		self.workloads = workloads 
		self.workload_assignments_for_node = workload_assignments_for_node 

		self.add_node_selector_constraint()

