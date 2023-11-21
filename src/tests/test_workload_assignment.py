import unittest 
from resources.WorkloadAssignment import Workloadassignment

class Test_Workload_Assignment(unittest.TestCase): 
    
	def testWorkload(self):  
		num_nodes = 4 
		num_workloads = 4
		wl_assignment = Workloadassignment(num_nodes, num_workloads) 

		for node_idx in range(num_nodes): 
			for workload_idx in range(num_workloads): 
				wl_assignment.set(workload_idx, node_idx, "node-"+str(node_idx)+"-wl-"+str(workload_idx))
		
		for node in range(num_nodes): 
			wl_for_node = wl_assignment.get_workloads_for_node(node) 
			for wl in wl_for_node: 
				assert("node-"+str(node) in wl)

