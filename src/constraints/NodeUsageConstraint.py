from resources.WorkloadAssignment import WorkloadAssignment  
from resources.node.Node import Node 
import gurobipy as gp  

class NodeUsageConstraint: 
    
	def generate_constraint(self): 
		curr_node_is_active = self.model.addVar(vtype='B', name="computenode"+ self.nodes[self.node_idx].name) 
		workload_assignment_vars_for_current_node = self.workload_assignments.get_workloads_for_node(self.node_idx) 

		self.model.addGenConstrOr(curr_node_is_active, workload_assignment_vars_for_current_node)  

		# TODO: consider moving  
		self.model.addConstr(gp.quicksum(workload_assignment_vars_for_current_node) <= 110) 
		return curr_node_is_active  
		
	def __init__(self, model, nodes: list[Node], node_idx, workload_assignments: WorkloadAssignment): 
		self.model = model  
		self.nodes = nodes 
		self.node_idx = node_idx 
		self.workload_assignments = workload_assignments  

		self.decision_var = self.generate_constraint()
