from resources.NodePool import NodePool
from resources.cloud_provider.CloudProvider import CloudProvider
from resources.NodePool import NodePool

from resources.cloud_provider.google_cloud.ProductCatalog import ProductCatalog 

from google.cloud import container_v1
from google.cloud import compute_v1

from helper.resource_parser import gb_to_mi

class GoogleCloud(CloudProvider): 
    
	def __init__(self, cluster_name: str, cluster_region: str, project_id: str): 
		self.client = container_v1.ClusterManagerClient()    

		self.compute = compute_v1.InstancesClient() 
		self.instance_group = compute_v1.InstanceGroupsClient()
		self.instance_group_manager = compute_v1.InstanceGroupManagersClient() 

		self.cluster_name = cluster_name 
		self.cluster_region = cluster_region 
		self.project_id = project_id
		self.catalog = ProductCatalog()
	
	def get_node_pools(self):
		 # Initialize request argument(s)
		request = container_v1.ListClustersRequest(parent=f"projects/{self.cluster_name}/locations/{self.cluster_region}", project_id=self.project_id)

		# Make the request
		response = self.client.list_clusters(request=request)
		# Handle the response 

		pools :list[NodePool] = []

		for cluster_idx in range(len(response.clusters)):   
			cluster = response.clusters[cluster_idx] 

			if(cluster.name == self.cluster_name): 
				for node_pool_idx in range(len(cluster.node_pools)): 
					pool = cluster.node_pools[node_pool_idx] 
					# TODO: Get current node count for pool?  
					manager_url = pool.instance_group_urls[0] if len(pool.instance_group_urls) == 1 else None
					pools.append(NodePool(pool.name, pool.config.machine_type, manager_url = manager_url))

		return pools 
	
	def parse_node_pool_from_node_label(self, node_labels: dict): 
		if node_labels and "cloud.google.com/gke-nodepool" in node_labels: 
			return node_labels["cloud.google.com/gke-nodepool"] 
		return None  
	
	def get_cost_per_hour_for_node_pool(self, pool: NodePool) -> float:
		return self.catalog.get_price_for_machine_name(pool.provider_machine_name)
	
	def get_all_potential_node_pools(self): 
		machine_types = self.catalog.machines  
		pools = []
		for type in machine_types:  
			machine_name = type["name"]
			pools.append(NodePool(f"virtual-pool-{machine_name}", type["name"])) 
		
		return pools

	def get_allocatable_memory_for_node_pool(self, pool: NodePool) -> int: 
		config = self.catalog.get_config_for_package_name(pool.provider_machine_name)
		if config is not None:   
			total_gb_memory = config["gbMemory"] 

			if total_gb_memory <= 1:  
				# TODO: Mibibytes used here 
				return gb_to_mi(1) - 255  
			
			allocatable_memory = 0 
			# https://learnk8s.io/allocatable-resources 
			# 25% of the first 4gb 

			rest_gb_memory = total_gb_memory 
			iterations = [
				 {"amount": 4, "av": 0.75},
				 {"amount": 4, "av": 0.80},
				 {"amount": 8, "av": 0.90}, 
				 {"amount": 112, "av": 0.94},
				 {"amount": 1000, "av": 0.98}
				]  
			iteration = 0
			while rest_gb_memory > 0: 
				if rest_gb_memory - iterations[iteration]["amount"] > 0: 
					rest_gb_memory = rest_gb_memory-iterations[iteration]["amount"]
					allocatable_memory += iterations[iteration]["amount"] * iterations[iteration]["av"]
				else:  
					allocatable_memory += rest_gb_memory * iterations[iteration]["av"] 
					rest_gb_memory = 0
				iteration += 1

			return gb_to_mi(allocatable_memory)
		return None 

	def get_allocatable_cpu_m_for_node_pool(self, pool: NodePool) -> float: 
		config = self.catalog.get_config_for_package_name(pool.provider_machine_name)
		
		if config is not None: 
			allocatable_cpu = 0 

			if 'sharedCore' in config and config["sharedCore"] == True: 
				return config["vcpu"] * 1000 - 1060

			for core_idx in range(config["vcpu"]): 
				if core_idx == 0: 
					allocatable_cpu += 0.94 * 1000 
				elif core_idx == 1: 
					allocatable_cpu += 0.99 * 1000 
				elif core_idx < 4: 
					allocatable_cpu += 0.995 * 1000 
				else: 
					allocatable_cpu += 0.9975 * 1000 
			return allocatable_cpu
		
		return None	 
	
	def query_status_of_cluster_operation(self, op_id): 
		try: 
			request = container_v1.GetOperationRequest(name=f"projects/{self.project_id}/locations/{self.cluster_region}/operations/{op_id}")  
			response = self.client.get_operation(request=request) 
			if response.status == response.status.DONE: 
				return True 
		except Exception as e: 
			print("Operation error", e) 
			
		return False 

	def check_node_added_to_pool(self, operation_id): 
		return self.query_status_of_cluster_operation(operation_id) 
	
   
  

	def add_node_to_node_pool(self, pool_name, node_count):  
		try : 
			request = container_v1.SetNodePoolSizeRequest( 
				name=f"projects/{self.project_id}/locations/{self.cluster_region}/clusters/{self.cluster_name}/nodePools/"+pool_name,
				node_count=node_count,
			)
			
			operation = self.client.set_node_pool_size(request=request)  
			
			return operation.name 
		except Exception as e: 
			print("Error ", e) 
			return None  

	def __get_instance_group_manager_for_node_name(self, name): 
		try: 
			request = compute_v1.GetInstanceRequest( 
				instance=name,
				project=self.project_id,
				zone=self.cluster_region
			) 
			response = self.compute.get(request)
			if response is not None and response.metadata: 
				for entry in response.metadata.items: 
					if entry.key == "created-by" and "instanceGroupManagers" in entry.value: 
						return entry.value 
					
		except Exception as e: 
			print("Error ", e)

	def __parse_group_manager_from_string(self, group_manager): 
		return group_manager.split("instanceGroupManagers/")[1] 
	
	def __remove_instance_from_group(self, group_manager, instance_name):  
		zone = self.cluster_region
		project = self.project_id
		try: 
			request = compute_v1.DeleteInstancesInstanceGroupManagerRequest(
				project=project,
				zone=zone, 
				instance_group_manager=group_manager,
				instance_group_managers_delete_instances_request_resource=compute_v1.InstanceGroupManagersDeleteInstancesRequest(instances=[ 
					f"zones/{zone}/instances/{instance_name}"
				])
			) 
			response = self.instance_group_manager.delete_instances(request)
		except Exception as e: 
			print("Error ", e) 

	def delete_node(self, node_name:str): 
		group_manager = self.__get_instance_group_manager_for_node_name(node_name)  
		self.__remove_instance_from_group(self.__parse_group_manager_from_string(group_manager), node_name) 

	def __get_instance_group_manager_for_machine_type(self, machine_type):  
		pass 

	# Problem: Only works for running instances
	def add_node_from_pool_url(self, manager_url, additional_nodes: int): 
		# TODO: Parse zone and project
		instance_group_manager = manager_url.split("/instanceGroupManagers/")[1]
		zone = self.cluster_region
		project = self.project_id
		print("Adding compute node for instancegroup manager", instance_group_manager)
		request = compute_v1.GetInstanceGroupManagerRequest(
			project=project,
			zone=zone, 
			instance_group_manager=instance_group_manager)

		response = self.instance_group_manager.get(request=request)  

		new_size = response.target_size + additional_nodes 

		resize_request = compute_v1.ResizeInstanceGroupManagerRequest(
			project=project,
			zone=zone, 
			instance_group_manager=instance_group_manager,
			size=new_size
		)  

		response = self.instance_group_manager.resize(request=resize_request) 

		return response 
	
	def increase_node_instance_count(self, manager_url, inc_count): 
		return self.add_node_from_pool_url(manager_url, inc_count) 







		#self.__remove_instance_from_group(group_manager.split("instanceGroupManagers/")[1], node_name) 
 



	



	
