

class Config: 

	def __init__(self, **kwargs): 
		self.restrict_k8_node_pools = kwargs.get('restrict_k8_node_pools', []) 
		self.boot_namespaces = kwargs.get('boot_namespaces', []) 
		self.protected_namespaces = kwargs.get('protected_namespaces', []) 

		self.disabled_vpa = kwargs.get('disable_vpa', True) 

		self.dry_run = kwargs.get('dry_run', True)  
		""" 
		Model config 
		""" 
		self.max_percentage_nodes_to_reschedule_per_iteration = kwargs.get('max_percentage_nodes_to_reschedule_per_iteration', 1) 
		self.use_model_timelimit = kwargs.get('use_model_timelimit', True) 
		self.use_early_stopping_objective = kwargs.get('use_early_stopping_objective', False)  

		"""
		Rescheduling config 
		"""
		self.reschedule_label = kwargs.get('reschedule_label', 'kinema-optimization-key')
		self.cordon_non_optimal_nodes = False

		self.default_optimizer_steps = [{
			"name": "cost_per_hour", 
			"weight": 2
		}, 
		{ 
			"name": "virtual_node_count", 
			"weight": 1
		},
		{ 
			"name": "increase_node_spread_by_count", 
			"weight": 1
		}, 
		{
			"name": "pods_to_reschedule", 
			"weight":1
		}, 
	]
		self.optimizer_steps = kwargs.get('optimizer_steps', self.default_optimizer_steps)
