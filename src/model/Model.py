
from resources.workload import Workload 
from resources.node.Node import Node, ensure_node_names_are_unique, calculate_hour_price_for_node_list, calc_resource_utilization
from resources.pod_disruption_budget import Pod_disruption_budget  
from resources.WorkloadAssignment import WorkloadAssignment
from resources.Config import Config

from constraints.NodeUsageConstraint import NodeUsageConstraint
from constraints.WorkloadAssignmentConstraint import WorkloadAssignmentConstraint 
from constraints.ResourceConstraint import ResourceConstraint  
from constraints.RescheduleConstraint import RescheduleConstraint 
from constraints.NodeTaintConstraint import NodeTaintConstraint 
from constraints.NodeSelectorConstraint import NodeSelectorConstraint 
from constraints.PodDisruptionBudgetConstraint import PodDisruptionBudgetConstraint
 

from helper.stat_collector import Stat_collector 
import gurobipy as gp  

"""
Main difference of model v2 vs. model v1 
is the change to the iterative nature. 
Previously, the model was used to find 
an iterative next step towards the optimum. 

Now we want to find the current optimal placement, 
while the movement of the pods and the evaluation of 
the steps is done by the Kinema executor
""" 

class ModelV2: 

	def __init__(self, workloads: list[Workload], k8_nodes: list[Node], virtual_nodes: list[Node], pdb: list[Pod_disruption_budget], iteration: int, stat_collector: Stat_collector, config: Config, k8):  
		self.workloads = workloads 
		self.k8_nodes = k8_nodes 
		self.virtual_nodes = virtual_nodes 

		self.nodes = [*self.k8_nodes, *self.virtual_nodes] 
		if ensure_node_names_are_unique(self.nodes) is False:
			raise Exception("Node names must be unique") 

		self.pdb = pdb 
		self.iteration = iteration 
		self.stat_collector = stat_collector   

		self.workload_assignments = WorkloadAssignment(len(self.nodes), len(self.workloads))

		self.model = gp.Model()   
		self.config = config  
		self.k8 = k8 

		self.node_usage_vars = []  

		# self.coefficient = -1 if len(self.virtual_nodes) > 0 else 1
		self.coefficient = 1

		# TODO: A renaming of this var would be good - currently hard to 
		# understand what the vars actually do  
		self.reschedule_vars = [] 
		
		self.apply_vpa_recommendation_vars = [] 

		self.unused_cpu_resources_per_node = [] 
		self.unused_memory_resources_per_node = []

		self.node_results : list[Node] = [] 
		self.booting_up_virtual_nodes = False 
		self.workload_results = [] 

	def __setup_constraints(self):  	 
		for workload_index, _ in enumerate(self.workloads): 
			WorkloadAssignmentConstraint(self.model, workload_index, self.workloads, self.nodes, self.workload_assignments) 
			self.apply_vpa_recommendation_vars.append(self.model.addVar(vtype='B', name="workload"+self.workloads[workload_index].name+"-reboot-for-recommendation") )

		reschedule_constraint = RescheduleConstraint(self.model, self.workloads, self.nodes, self.workload_assignments)  
		self.reschedule_vars = reschedule_constraint.reschedule_vars

		for wl_index, wl in enumerate(self.workloads):
			self.model.addConstr( (self.apply_vpa_recommendation_vars[wl_index] == 1) >> (reschedule_constraint.reschedule_vars[wl_index] == 1) ) 

			wl = self.workloads[wl_index]  
			if wl.has_recommendation() == False: 
				self.model.addConstr(self.apply_vpa_recommendation_vars[wl_index] == 0) 
			
			for namespace in self.config.protected_namespaces: 
				if wl.namespace == namespace: 
					# print(wl.name, "WL is in protected namespace")
					self.model.addConstr(reschedule_constraint.reschedule_vars[wl_index] == 0) 
			if wl.is_critical_workload:  
					# print("Add constr for ", wl.name, " as the pod is critical")
					self.model.addConstr(reschedule_constraint.reschedule_vars[wl_index] == 0) 

		self.model.addConstr(gp.quicksum(reschedule_constraint.reschedule_vars) <= len(self.workloads) * self.config.max_percentage_nodes_to_reschedule_per_iteration)

		
		# PodDisruptionBudgetConstraint(self.model, self.pdb, self.workloads, self.workload_assignments, reschedule_constraint.reschedule_vars, self.apply_vpa_recommendation_vars) 

		""" 
		Take a workload perspective 

		The constraints for a workload to be able to run on a given node are added 

		The following decision variables decide if a specific node is used for workloads. 
		Once a single workload should be installed on this node, the decision variable becomes true. 
		"""
		for node_idx, node in enumerate(self.nodes):

			node_usage_constr = NodeUsageConstraint(self.model, self.nodes, node_idx, self.workload_assignments)  
			if node.isVirtual is False:
				node_usage_constr.decision_var.Start = 1
			
			self.node_usage_vars.append(node_usage_constr.decision_var)  

			""" 
			Column of workload assignment binaries 
			This turns the current node is used binary to true if at least one workload 
			is deployed 
			"""
			workload_assignments_for_node = self.workload_assignments.get_workloads_for_node(node_idx)
			ResourceConstraint(self.model, 'cpu', workload_assignments_for_node, self.workloads, self.k8.daemon_sets, node_usage_constr.decision_var, self.nodes[node_idx].allocatable_cpu, self.apply_vpa_recommendation_vars) 
			ResourceConstraint(self.model, 'memory', workload_assignments_for_node, self.workloads, self.k8.daemon_sets, node_usage_constr.decision_var, self.nodes[node_idx].allocatable_memory, self.apply_vpa_recommendation_vars)

			# TODO: Add config here 
			if True:  
				ResourceConstraint(self.model, 'cpu', workload_assignments_for_node, self.workloads, self.k8.daemon_sets, node_usage_constr.decision_var, self.nodes[node_idx].allocatable_cpu, self.apply_vpa_recommendation_vars, True) 
				ResourceConstraint(self.model, 'memory', workload_assignments_for_node, self.workloads, self.k8.daemon_sets, node_usage_constr.decision_var, self.nodes[node_idx].allocatable_memory, self.apply_vpa_recommendation_vars, True)
			
			if len(node.taints) > 0:    
				NodeTaintConstraint(self.model, node, self.workloads, workload_assignments_for_node)
			
			#NodeSelectorConstraint(self.model, node, self.workloads, workload_assignments_for_node) 

			""" 
			Resource utilization based on requests 
			"""
			unused_cpu_var = self.model.addVar(name="cpu_wastage"+str(node_idx))    
			unused_memory_var =  self.model.addVar(name="memory_wastage"+str(node_idx))   
			
			allocated_cpu_var = self.model.addVar(name="allocated-cpu"+str(node_idx))    
			allocated_memory_var = self.model.addVar(name="allocated-memory"+str(node_idx)) 

			self.model.addConstr(allocated_cpu_var == gp.quicksum(node.get_allocated_cpu(node_idx, self.workloads, self.k8.daemon_sets, self.workload_assignments, self.node_usage_vars[node_idx])))
			self.model.addConstr(allocated_memory_var == gp.quicksum(node.get_allocated_memory(node_idx, self.workloads, self.k8.daemon_sets, self.workload_assignments, self.node_usage_vars[node_idx])))

			self.model.addConstr(unused_cpu_var == self.node_usage_vars[node_idx] * (node.allocatable_cpu - allocated_cpu_var)) 
			self.model.addConstr(unused_memory_var == self.node_usage_vars[node_idx] * (node.allocatable_memory - allocated_memory_var)) 
			
			self.unused_cpu_resources_per_node.append(unused_cpu_var) 
			self.unused_memory_resources_per_node.append(unused_memory_var)  

		# Debug - force bootup of a virtual node 
		if len(self.virtual_nodes) > 0 and False:  
			print("Adding debug constraint to boot new node")
			self.model.addConstr(gp.quicksum([self.node_usage_vars[node_usage_var_idx] * 1 if self.nodes[node_usage_var_idx].isVirtual is True else 0 for node_usage_var_idx in range(len(self.node_usage_vars))]) >= 1)

	def __setup_objectives(self):   

		objective_templates = { 
			"cost_per_hour": self.coefficient*gp.quicksum([self.node_usage_vars[node_usage_var_idx] * self.nodes[node_usage_var_idx].cost_per_hour for node_usage_var_idx in range(len(self.node_usage_vars))]), 
			"total_unused_resources": self.coefficient *  (gp.quicksum(self.unused_cpu_resources_per_node) + gp.quicksum(self.unused_memory_resources_per_node)), 
			"pods_to_reschedule": gp.quicksum(self.reschedule_vars), 
			"apply_vpa_recommendation_count": -1 * gp.quicksum(self.apply_vpa_recommendation_vars), 
			"virtual_node_count": gp.quicksum([self.node_usage_vars[node_usage_var_idx] * 1 if self.nodes[node_usage_var_idx].isVirtual is True else 0 for node_usage_var_idx in range(len(self.node_usage_vars))]),
			"increase_node_spread_by_count": -1 * gp.quicksum([self.node_usage_vars[node_usage_var_idx] for node_usage_var_idx in range(len(self.node_usage_vars))]),
		} 

		for step_idx, optimizer_step in enumerate(self.config.optimizer_steps):  
			self.model.setObjectiveN(objective_templates[optimizer_step["name"]], step_idx, optimizer_step["weight"]) 

	def __optimize(self): 
		if self.config.use_model_timelimit is not False:  
			self.model.Params.TimeLimit = 5 * (self.iteration+1) 

		if self.config.use_early_stopping_objective is not False and self.config.optimizer_steps[0]["name"] == "cost_per_hour":  
			# If we can make at least a x % cost improvment 
			# We should stop the optimization and execute the plan 
			hour_price = calculate_hour_price_for_node_list(self.k8_nodes)  
			min_optimization_percentage = 0.3
			optimized_hour_price = hour_price * (1-min_optimization_percentage)
			print("Optimized hour price", str(optimized_hour_price))
			self.model.params.BestObjStop = optimized_hour_price + 1e-4

		self.model.optimize()   
	
	def __print_solution(self, solution_index, objective_count): 
		self.model.params.SolutionNumber = solution_index  
		
		for o in range(objective_count): 
			self.model.params.ObjNumber = o  
			objective_name = self.config.optimizer_steps[o]["name"]
			 
			if solution_index == 0:  
				#coefficient = self.coefficient if objective_name != 'apply_vpa_recommendation_count' and objective_name != 'cost_per_hour' else -1
				coefficient = 1
				self.stat_collector.collect_stat(objective_name, coefficient * round(self.model.ObjNVal, 2))
 
	def __handle_result(self):  
		print(f"Optimized cost per hour: {self.model.objVal}")   

		solution_count  = self.model.SolCount 
		objective_count = self.model.NumObj   

		for solution_index in range(solution_count): 
			self.__print_solution(solution_index, objective_count)

	def __handle_action_of_optimal_solution(self): 
		for node_index, node in enumerate(self.nodes):  
			""" 
			Newly added nodes 
			"""
			if(self.node_usage_vars[node_index].X > 0):  
				if node.isVirtual is True:   
					# self.booting_up_virtual_nodes = True  
					copy_node = node.copy()  
					copy_node.name = copy_node.name + "-newly-booted-"+str(node_index)   
					# copy_node.isVirtual = False 
					self.node_results.append(copy_node) 
				else: 
					self.node_results.append(node) 

		for workload_index, workload in enumerate(self.workloads):   
			for node_index, node in enumerate(self.nodes): 
				
				current_workload_running_on_current_node = self.workload_assignments.get(workload_index, node_index) 
				
				if current_workload_running_on_current_node.X > 0:  
					self.stat_collector.increment_stat("workload_count")
					workload.current_node_name = node.name
					
					vpa_adjustment = self.apply_vpa_recommendation_vars[workload_index].X 
					if(vpa_adjustment > 0): 
						print("wl ", workload.name, " is being resized to recommendation") 
						workload.apply_request_recommendation()
					if vpa_adjustment < 1 and workload.has_recommendation(): 
						print("wl ", workload.name, " is not resized") 
						
					self.workload_results.append(workload)
					#print(workloads[workload_index].name, " should now run on ", nodes[node_index].name, " previous ", workloads[workload_index].current_node_name) 
		
			""" 
			It is important that we only count pods_to_reschedule here 
			as otherwise we are only booting up a new node
			"""
		for var in self.reschedule_vars: 
			if var.X == 1:  
				self.stat_collector.increment_stat("pods_to_reschedule")
			
				
	def __collect_optimal_result_stats(self): 
	
		self.stat_collector.collect_stats({ 
			"total_node_count": len(self.node_results), 
			"cost_per_hour": round(calculate_hour_price_for_node_list(self.node_results), 2)
		}) 

		allocatable_cpu, allocatable_memory, allocated_cpu, allocated_memory = calc_resource_utilization(self.nodes, self.workloads, self.k8.daemon_sets, self.workload_assignments, False, False, self.node_usage_vars) 
		self.stat_collector.collect_stats({ 
			"allocatable_cpu": allocatable_cpu, 
			"allocated_cpu": allocated_cpu, 
			"allocatable_memory": allocatable_memory, 
			"allocated_memory": allocated_memory, 
			"total_node_count": len(self.node_results), 
			"cost_per_hour": round(calculate_hour_price_for_node_list(self.node_results), 2)
		})  

	def __collect_initial_stats(self): 
		allocatable_cpu, allocatable_memory, allocated_cpu, allocated_memory = calc_resource_utilization(self.nodes, self.workloads, self.k8.daemon_sets, self.workload_assignments, True, False, []) 

		self.stat_collector.collect_stats({  
            "cost_per_hour": round(calculate_hour_price_for_node_list(self.k8_nodes), 2),
            "pods_to_reschedule": 0, 
            "new_nodes_to_boot":0,  
            "drain_node_count":0,
            "iteration_duration":None, 
            "allocated_cpu":allocated_cpu,
            "allocated_memory":allocated_memory, 
            "total_node_count": len(self.k8_nodes),
            "allocatable_cpu": allocatable_cpu,
            "allocatable_memory":allocatable_memory,  
	    	"total_unused_resources": allocatable_cpu - allocated_cpu + allocatable_memory - allocated_memory,
            "workload_count":len(self.workloads)
        })

	def run_optimization(self):
		self.stat_collector.collect_stat("iteration", self.iteration)

		self.__setup_constraints()   
		self.__setup_objectives()  
		self.__optimize()   

		if self.iteration == 0: 
			self.__collect_initial_stats()   
			return self.workloads, self.k8_nodes, self.booting_up_virtual_nodes
		
		else: 
			self.__handle_result() 
			self.__handle_action_of_optimal_solution()  
			self.__collect_optimal_result_stats()  
			
			self.model.dispose()
			return self.workload_results, self.node_results, self.booting_up_virtual_nodes


