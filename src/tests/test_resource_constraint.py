import unittest 
from resources.WorkloadAssignment import Workloadassignment    
from constraints.WorkloadAssignmentConstraint import Workload_assignment_constraint 
from constraints.NodeUsageConstraint import Node_usage_constraint  
from constraints.ResourceConstraint import Resource_constraint

from resources.workload import Workload
from resources.node.Node import Node, ensure_node_names_are_unique

import gurobipy as gp  

class Test_Resource_Constraint(unittest.TestCase): 

	def test_constraint(self):  
		m = gp.Model()  
		node_count = 3 
		workload_count = 3
		nodes : list[Node] = [] 
		workloads = []

		for idx in range(node_count):  
			nodes.append(Node({ 
            "name": "e2-standard-8"+str(idx),
            "poolname":"e2-standard-8",
            "allocatableCPU":1000,
            "allocatableMemory":2000, 
            "costPerHour":0.32
        })) 
			
		if ensure_node_names_are_unique(nodes) is False: 
			raise Exception("Node names are not unique")
		
		for idx in range(workload_count): 
			workloads.append(Workload({ 
            "name":"frontend",
            "cpuRequest": 500,
            "memoryRequest":600,  
	    	"currentNodeName":nodes[idx].name
		}))
		
		workload_assignments = Workloadassignment(node_count, workload_count) 
		
		for workload_idx in range(len(workloads)): 
			Workload_assignment_constraint(m, workload_idx, workloads, nodes, workload_assignments)

		node_usage_constraints = []
		for node_idx in range(len(nodes)):  
			constr = Node_usage_constraint(m, nodes, node_idx, workload_assignments) 
			node_usage_constraints.append(constr.decision_var)  

			workload_assignments_for_node = workload_assignments.get_workloads_for_node(node_idx)
			Resource_constraint(m, 'cpu', workload_assignments_for_node, workloads, [], constr.decision_var, nodes[node_idx].allocatable_cpu, [])
			Resource_constraint(m, 'memory', workload_assignments_for_node, workloads, [], constr.decision_var, nodes[node_idx].allocatable_memory, [])
		
		m.setObjectiveN(gp.quicksum(node_usage_constraints), 0) 

		m.optimize() 
		print(f"Optimized node count: {m.objVal}") 
		assert(m.objVal == 2)





		



		

