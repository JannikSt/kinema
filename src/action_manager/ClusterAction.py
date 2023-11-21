
from action_manager.ClusterActionTypes import ClusterActionTypes 
from resources.node.Node import Node  
from resources.node.NodeStatus import NodeStatus
from resources.workload import Workload  
from resources.KubernetesCluster import KubernetesCluster 
import time

class ClusterAction: 

	def __init__(self, type: ClusterActionTypes, cluster: KubernetesCluster,  **kwargs):  
		self.type = type 
		self.node : Node = kwargs.get('node', None)  
		self.workload : Workload = kwargs.get('workload', None)  
		self.cluster : KubernetesCluster = cluster

		if type == ClusterActionTypes.BOOT and self.node == None: 
			raise Exception("Missing parameter") 
		if type == ClusterActionTypes.RESCHEDULE and self.workload == None: 
			raise Exception("Missing parameter")

		self.completed = False  
		self.failed = False 
	
	""" 
	All actions related to booting up new nodes
	The logic here is handled by the KubernetesCluster Object  
	"""
	def __prepare_node_boot(self):
		self.cluster.prepare_boot_node(self.node)

	def __execute_node_boot(self):  
		# TODO: Check if all parameters are set 
		self.cluster.boot_node(self.node)
		print("Executing a bootup", self.node.name)  
	
	def __check_node_boot(self):  
		# TODO: Check if all parameters are set 
		print("Checking a bootup", self.node.name)  
	
	""" 
	All actions related to draining a node 
	""" 
	def __prepare_node_drain(self): 
		print("Preparing node drain") 
		self.cluster.mark_node_as_unschedulable(self.node.name) 

	def __execute_node_drain(self): 
		print("Draining node", self.node.name)  
		self.cluster.drain_node(self.node)
	
	def __check_node_drain(self): 
		pass

	""" 
	All actions related to rescheduling workloads 
	"""
	def __execute_workload_reschedule(self):  
		completed = False 

		try: 
			self.cluster.evict_pod(self.workload.name, self.workload.namespace)  
			self.completed = True
		except Exception as e: 
			print("Could not evict workload ")   
			self.failed = True
			

	def __check_workload_reschedule(self): 
		print("Checking a workload reschedule")     
		return self.completed

	def prepare(self): 
		match self.type: 
			case ClusterActionTypes.BOOT:  
				self.__prepare_node_boot()  
			case ClusterActionTypes.DRAIN: 
				self.__prepare_node_drain()
			case _:
				print("No prepare step for ", self.type.name)

	""" 
	General cluster action functions
	"""
	def execute(self): 
		match self.type: 
			case ClusterActionTypes.BOOT:  
				self.__execute_node_boot() 
			case ClusterActionTypes.DRAIN: 
				self.__execute_node_drain() 
			case ClusterActionTypes.RESCHEDULE: 
				self.__execute_workload_reschedule() 
			case _: 
				print("Unknown cluster action type", self.type.name)
	
	def check_completed(self): 
		match self.type: 
			case ClusterActionTypes.BOOT:  
				self.__check_node_boot() 
			case ClusterActionTypes.DRAIN: 
				self.__check_node_drain() 
			case ClusterActionTypes.RESCHEDULE: 
				self.__check_workload_reschedule() 
			case _: 
				print("Unknown cluster action type", self.type.name) 
		
		return self.completed 



		