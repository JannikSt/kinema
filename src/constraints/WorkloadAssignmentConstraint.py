
from resources.workload import Workload
from resources.node.Node import Node  
from resources.WorkloadAssignment import WorkloadAssignment  
import random 
import gurobipy as gp 

class WorkloadAssignmentConstraint: 
	
	def ensure_node_name_exists(self, name): 
		for node in self.nodes: 
			if node.name == name: 
				return True 
		return False 


	def only_one_node_per_workload_assignment(self): 
		node_assignment_vars = []  

		workload = self.workloads[self.workload_idx]  
		
		if self.ensure_node_name_exists(workload.current_node_name) == False: 
			self.current_node_name = None
			

		if workload.current_node_name is None: 
			# Choose random node 
			random_node_index = random.randint(0, len(self.nodes)-1)  
			print(f"Workload {workload.name} does not have a node yet - assignin random node idx {str(random_node_index)}")  
			workload.current_node_name = self.nodes[random_node_index].name



		for node_idx in range(len(self.nodes)):  

			node = self.nodes[node_idx]

			assignment_var = self.model.addVar(vtype='B', name=workload.name+"-on-node-"+node.name) 
			node_assignment_vars.append(assignment_var)  

			self.workload_assignment.set(self.workload_idx, node_idx, assignment_var) 

			if node.name == workload.current_node_name:
				assignment_var.Start = 1
		
		self.model.addConstr(gp.quicksum(node_assignment_vars) == 1)


	def __init__(self, model, workload_idx, workloads : list[Workload], nodes: list[Node], workload_assignment: WorkloadAssignment): 
		self.model = model  
		self.workload_idx =  workload_idx 
		self.workloads = workloads   
		self.nodes = nodes  
		self.workload_assignment = workload_assignment 

		self.only_one_node_per_workload_assignment()
	

