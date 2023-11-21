from resources.KubernetesCluster import KubernetesCluster
from resources.Config import Config 
from resources.workload import Workload 
from resources.node.Node import Node  
from helper.random_string import random_string   

from copy import deepcopy

import time 

class Rescheduler: 

	def __init__(self, cluster: KubernetesCluster, optimized_k8_nodes: list[Node], initial_nodes: list[Node], **kwargs): 

		self.cluster = cluster 
		self.config = kwargs.get('config', Config())
		self.iteration_key = random_string(6) 
		
		self.optimized_nodes_pre_boot : list[Node] = optimized_k8_nodes 
		self.optimized_node_names_post_boot : list[str] = []

		self.initial_nodes : list[Node] = deepcopy(initial_nodes) 

		self.state = {}
	
	def __calculate_boot_strategy(self) -> dict: 
		""" 
		Calculate a plan which nodes will be booted from the virtual nodes and 
		which nodes 
		"""
		node_pool_managers = {} 

		for node in self.initial_nodes: 
			print("Initial node", node.name, " machine", node.node_pool.provider_machine_name)
		for node in self.optimized_nodes_pre_boot:  
			print("Optimal", node.name, " machine", node.node_pool.provider_machine_name)
			if node.isVirtual == True:  
				manager_url = node.node_pool.manager_url
				if node.node_pool.manager_url in node_pool_managers.keys():
					node_pool_managers[manager_url] += 1 
				else: 
					node_pool_managers[manager_url] = 1 
		
		print("Boot strategy calculated ", node_pool_managers) 
		return node_pool_managers  
	
	def __wait_until_all_nodes_in_cluster(self, boot_strategy):   
		# Sort out all nodes that we knew previously  
		# Initial nodes also contain all node names that are optimal 
		initial_node_names = [node.name for node in self.initial_nodes] 
		
		# We utilize the boot strategy to count the nodes 
		ready_nodes = {} 
		for key in boot_strategy.keys(): 
			ready_nodes[key] = 0
		
		known_newly_booted_nodes = []  

		all_nodes_booted = False  
		check_count = 0 

		while all_nodes_booted == False and check_count < 10:  
			self.cluster.sync() 
			print("Checking if all nodes are in cluster")
			for node in self.cluster.nodes: 
				if node.name not in initial_node_names and node.name not in known_newly_booted_nodes: 
					if node.node_pool.manager_url in ready_nodes.keys(): 
						print(node.name, " is ready")
						ready_nodes[node.node_pool.manager_url] += 1 
						known_newly_booted_nodes.append(node.name)  
			
			ready_check = True  
			print(ready_nodes)
			for key in boot_strategy.keys(): 
				if ready_nodes[key] < boot_strategy[key]: 
					print("Key ", key, " ready: ", ready_nodes[key], " want: ", boot_strategy[key])
					ready_check = False 
			
			all_nodes_booted = ready_check  
			if ready_check == False:  
				print("Not all nodes booted yet. Waiting.") 
				time.sleep(10) 
				check_count += 1
		
		optimized_node_names_post_boot = []  
		for node in self.optimized_nodes_pre_boot: 
			if node.isVirtual == False: 
				optimized_node_names_post_boot.append(node) 
		
		optimized_node_names_post_boot.extend(known_newly_booted_nodes)

		self.optimized_node_names_post_boot = optimized_node_names_post_boot  
		print("Wait for nodes in cluster completed.")

	def __add_label_to_optimized_nodes(self):  
		for node_name in self.optimized_node_names_post_boot: 
			self.cluster.update_node_label(node_name, self.config.reschedule_label, self.iteration_key)

	def __cordon_nodes(self):  
		if self.config.cordon_non_optimal_nodes: 
			for node in self.cluster.nodes:  
				if node.name not in self.optimized_node_names_post_boot: 
					self.cluster.mark_node_as_unschedulable(node.name) 

	def __execute_boot_strategy(self): 
		boot_strategy = self.__calculate_boot_strategy()
		print(boot_strategy)

		#raise Exception("Breaker")
	
		if len(boot_strategy.keys()) == 0:  
			print("No new nodes to boot")
			return 

		success = self.cluster.add_multiple_nodes(boot_strategy)  
		if success: 
			self.__wait_until_all_nodes_in_cluster(boot_strategy) 
			self.__add_label_to_optimized_nodes() 
			self.__cordon_nodes() 


	def __calculate_reschedule_strategy(self):  
		deployments_to_reschedule = [] 
		for workload in self.cluster.workloads: 
			if workload.current_node_name not in self.optimized_node_names_post_boot: 
				if workload.deployment_name not in deployments_to_reschedule: 
					deployments_to_reschedule.append(workload.deployment_name) 
		return deployments_to_reschedule
	
	def __wait_for_rs_to_be_stable(self): 
		# TODO: How to find rs? 
		is_stable = False 
		check_count = 0 

		# TODO: Get initial names of replicasets, then query 

		pass  

	def __execute_reschedule_strategy(self):   
		print("Executing reschedule deployment") 
		deployments_to_reschedule = self.__calculate_reschedule_strategy()

		print("Deployments to reschedule", deployments_to_reschedule)
		for deployment in self.cluster.deployments: 
			if deployment.name in deployments_to_reschedule: 
				deployment.adjust_node_affinity(self.config.reschedule_label, self.iteration_key, self.cluster.apps_v1)

		self.__wait_for_rs_to_be_stable()

	def execute(self):   
		if self.config.dry_run:  
			print("Rescheduler is not active in dry run mode")
			return 
		
		self.__execute_boot_strategy() 
		self.__execute_reschedule_strategy()   

		print("Rescheduler completed")