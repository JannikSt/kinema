

class WorkloadAssignment: 
    
	def generate_assignment_list(self): 
		""" 
		Generate a 2D list with a row for each workload and a column for each node. 
		If a cell is true the workload is mapped to this workload
		"""  
		return  [['' for _ in range(self.node_count)] for r in range(self.workload_count)] 


	def __init__(self, node_count, workload_count): 
		self.node_count = node_count
		self.workload_count = workload_count

		self.workload_assignment = self.generate_assignment_list() 
	
	def get(self, workload_index, node_index): 
		return self.workload_assignment[workload_index][node_index] 

	def set(self, workload_index, node_index, content): 
		self.workload_assignment[workload_index][node_index] = content
	
	def get_workloads_for_node(self, node_index): 
		return [j[node_index] for j in self.workload_assignment]  

	def shape(self): 
		print(str(len(self.workload_assignment)) + "x" + str((len(self.workload_assignment[0]))))