from resources.NodePool import NodePool
from resources.cloud_provider.CloudProvider import CloudProvider
from resources.NodePool import NodePool

from resources.cloud_provider.google_cloud.ProductCatalog import ProductCatalog 

from google.cloud import container_v1
from google.cloud import compute_v1

from helper.resource_parser import gb_to_mi

# TODO: Build integration - AWS is currently not supported 
class AWS(CloudProvider): 
    
	def __init__(self, cluster_name: str, cluster_region: str):  
		pass 
	
	def get_node_pools(self):
		return []
	
	def parse_node_pool_from_node_label(self, node_labels: dict):  
		return node_labels["beta.kubernetes.io/instance-type"]
	
	def get_cost_per_hour_for_node_pool(self, pool: NodePool) -> float:
		return 0
	
	def get_all_potential_node_pools(self): 
		return []

	def get_allocatable_memory_for_node_pool(self, pool: NodePool) -> int: 
		return None 

	def get_allocatable_cpu_m_for_node_pool(self, pool: NodePool) -> float: 
		return None	 
	
	def query_status_of_cluster_operation(self, op_id): 
		return False 

	def check_node_added_to_pool(self, operation_id): 
		return False 

	def add_node_to_node_pool(self, pool_name, node_count):  
		return None 

	def delete_node(self, node_name:str): 
		return None  

	def increase_node_instance_count(self, manager_url: str, inc_count: int) -> any: 
		return None


	
