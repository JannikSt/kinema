


from resources.workload import Workload
import gurobipy as gp 

class ResourceConstraint: 

	def __init__(self, model, type: str, wl_assignment_vars_for_node, workloads : list[Workload], daemon_sets: list[Workload], curr_node_usage_var, max_node_capacity, apply_vpa_workload_vars, use_limit = False): 
		self.model = model 
		self.type = type 
		self.workload_assignment_vars_for_node = wl_assignment_vars_for_node  
		self.workloads = workloads  
		self.curr_node_usage_var = curr_node_usage_var  
		self.max_node_capacity = max_node_capacity 
		self.daemon_sets = daemon_sets  
		self.apply_vpa_recommendation_vars = apply_vpa_workload_vars 

		self.use_limit = use_limit

		self.get_resource_constraint()
	
	def _get_requests_for_workloads_on_node(self): 
		""" 
		Calculate the total requests for the workloads on the node 
		based on the model vars. 
		If a workload runs on the node (hence model var is true) we add 
		the workload to the total requests 
		"""   
		requests = [] 
		for workload_idx in range(len(self.workloads)):   
			is_recommendation_used_var = 0 if self.use_limit == True else self.apply_vpa_recommendation_vars[workload_idx]
			requests.append(self.workload_assignment_vars_for_node[workload_idx] * (1-is_recommendation_used_var) * self.workloads[workload_idx].get_resource_request(self.type, False, self.use_limit)) 	
			requests.append(self.workload_assignment_vars_for_node[workload_idx] * is_recommendation_used_var * self.workloads[workload_idx].get_resource_request(self.type, True))

		return requests 

	def _get_daemon_set_requests_for_node(self): 
		requests = [] 
		for daemon_set in self.daemon_sets: 
			requests.append(self.curr_node_usage_var * daemon_set.get_resource_request(self.type, False, self.use_limit)) 
		
		return requests

	def get_resource_constraint(self): 
		all_requests_for_node = [*self._get_daemon_set_requests_for_node(), *self._get_requests_for_workloads_on_node()] 
		self.model.addConstr(gp.quicksum(all_requests_for_node) <= self.max_node_capacity) 
	
