
from action_manager.ClusterAction import ClusterAction  
from action_manager.ClusterActionTypes import ClusterActionTypes 

from resources.workload import Workload 
from resources.node.Node import Node  
from resources.KubernetesCluster import KubernetesCluster

class ActionManager: 

	def __init__(self, optimized_workloads : list[Workload], optimized_k8_nodes: list[Node], initial_nodes: list[Node], initial_workloads: list[Workload], k8: KubernetesCluster): 
		self.optimized_workloads = optimized_workloads 
		self.optimized_k8_nodes = optimized_k8_nodes   

		self.initial_workloads = initial_workloads
		self.initial_nodes = initial_nodes

		self.k8 : KubernetesCluster = k8
		self.completed = False 

		self.actions : list[ClusterAction] = []

		self.__calculate_plan()
		# TODO: How to sync tasks such as bootup? 
		# If we have multiple tasks asking a nodepool to boot up? 

	def __calculate_plan(self):  
		""" 
		Which nodes to boot? 
		"""
		for node in self.optimized_k8_nodes: 
			if(node.isVirtual): 
				self.actions.append(ClusterAction(ClusterActionTypes.BOOT, self.k8, node=node))
				
		""" 
		Which workloads to reschedule? 
		""" 
		for workload in self.optimized_workloads: 
			reschedule_workload = False 
			for o_workload in self.initial_workloads: 
				if o_workload.name == workload.name:  
					""" 
					Current workload node name might be misleading here. 
					The optimizer sets this field to the node it should be running on 
					in the future 
					""" 
					if o_workload.current_node_name != workload.current_node_name:   
						reschedule_workload = True  
			
			if reschedule_workload:  
				# TODO: Reconsider parameters that are passed here 
				# TODO: Check if workload is simply rescheduled onto same node?
				self.actions.append(ClusterAction(ClusterActionTypes.RESCHEDULE, self.k8, workload=workload)) 
 

		""" 
		Which nodes to drain? 
		"""
		for node in self.initial_nodes: 
			drain_node = True 
			for o_node in self.optimized_k8_nodes: 
				if o_node.name == node.name: 
					drain_node = False 

			if drain_node: 
				self.actions.append(ClusterAction(ClusterActionTypes.DRAIN, self.k8, node=node))
		
	def __prepare(self): 
		for action in self.actions: 
			print("Preparing action ", action.type.name) 
			action.prepare() 

	def execute(self):  
		self.__prepare()

		for action in self.actions: 
			print("Executing action ", action.type.name) 
			action.execute() 
		
		self.__check_completed()
	
	def __check_completed(self): 
		for action in self.actions: 
			action_completed = action.check_completed() 
			if action_completed == False: 
				return False  
			
		return True




