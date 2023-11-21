from abc import ABC, abstractmethod 

from resources.NodePool import NodePool 

class CloudProvider(ABC): 
    
	def __init__(self): 
		pass 
	
	@abstractmethod
	def get_node_pools(self) -> list[NodePool]: 
		raise NotImplementedError("Get nodepools not implemented")  

	@abstractmethod 
	def add_node_to_node_pool(self, pool_name, count) -> None: 
		raise NotImplementedError("Get nodepools not implemented")  
	
	@abstractmethod
	def check_node_added_to_pool(self, operation_id) -> bool: 
		raise NotImplementedError("Check node add to pool not implemented") 
	
	@abstractmethod 
	def delete_node(self, node_name) -> None: 
		raise NotImplementedError("Get nodepools not implemented")   
	
	@abstractmethod
	def parse_node_pool_from_node_label(self) -> str: 
		raise NotImplementedError("Get nodepools not implemented")
	
	@abstractmethod
	def get_cost_per_hour_for_node_pool(self, pool: NodePool) -> float:  
		raise NotImplementedError("Get nodepools not implemented") 
	
	@abstractmethod
	def get_allocatable_cpu_m_for_node_pool(self, pool: NodePool) -> int:  
		raise NotImplementedError("Get nodepools not implemented")
	
	@abstractmethod
	def get_allocatable_memory_for_node_pool(self, pool: NodePool) -> float:  
		raise NotImplementedError("Get nodepools not implemented")
	
	@abstractmethod
	def get_all_potential_node_pools(self) -> list[NodePool]:  
		raise NotImplementedError("Get nodepools not implemented") 
	
	@abstractmethod
	def increase_node_instance_count(self, manager_url: str, inc_count: int) -> any: 
		raise NotImplementedError("Get nodepools not implemented") 

