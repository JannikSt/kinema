from resources.workload import Workload
from resources.node.Node import Node   
from resources.pod_disruption_budget import Pod_disruption_budget 
from resources.vpa import VPA  
from resources.NodePool import NodePool
from resources.Config import Config
from resources.Deployment import Deployment 

from resources.cloud_provider.CloudProvider import CloudProvider 

from kubernetes import client, config
from helper.resource_parser import parse_cpu_to_m, parse_memory_to_mi  
import os 
import time 


class KubernetesCluster:  

	def __init__(self, cloud_provider: CloudProvider, **kwargs):  

		# TODO: properly parse en  
		if os.environ.get("K8_LOAD_CONFIG") == "local": 
			config.load_kube_config()
		else:  
			config.load_kube_config()
			# config.load_incluster_config()
		
		self.optimizer_config = kwargs.get('config', Config())
		self.ignore_node_pool = kwargs.get('ignore_node_pool', False)

		self.v1 = client.CoreV1Api()   
		self.autoscaling = client.AutoscalingV2Api()
		self.policy = client.PolicyV1Api() 
		self.custom_objects = client.CustomObjectsApi() 
		self.apps_v1 = client.AppsV1Api()   
		self.events = client.EventsV1Api()  
		self.cloud_provider = cloud_provider

		self.daemon_sets : list[Workload] = []

		self.workloads : list[Workload] = [] 
		self.nodes : list[Node] = []   
		self.deployments : list[Deployment] = []
		self.pdbs : list[Pod_disruption_budget] = [] 
		self.vpas : list[VPA] = [] 

		self.virtual_nodes: list[Node] = []

		self.node_pools : list[NodePool] = [] 

		self.boot_node_queue : list[Node] = []
 
	
	def sync(self):  
		self.node_pools = self.cloud_provider.get_node_pools()

		self.__get_nodes() 
		self.__get_workloads()   
		self.__get_deployments()
		self.__get_pod_disruption_budget() 
		self.__get_vpa() 
		# self.__sync_current_pod_utilization() 

		self.__generate_virtual_nodes() 

		# TODO Trigger action from node to node pool  
		# TODO Add nodepool to virtual nodes 
		# TODO Sync task in action manager for bootup  

	def __generate_virtual_nodes(self): 

		RESTRICT_TO_EXISTING_POOLS = True 
		if RESTRICT_TO_EXISTING_POOLS: 
			virtual_pools = [] 
			for pool in self.node_pools: 
				if ("standard" in pool.provider_machine_name or "highmem" in pool.provider_machine_name or "highcpu" in pool.provider_machine_name) and "ts" in pool.name:   
					virtual_pools.append(pool)
		else: 
			virtual_pools = self.cloud_provider.get_all_potential_node_pools() 
		
		# TODO: Add setting to only boot existing node pools

		node_templates = []
		for pool in virtual_pools: 
			node_template = { 
				"name": pool.provider_machine_name, 
				"poolname": pool.name, 
				"node_pool": pool,
				"allocatableCPU": self.cloud_provider.get_allocatable_cpu_m_for_node_pool(pool), 
				"allocatableMemory": self.cloud_provider.get_allocatable_memory_for_node_pool(pool), 
				"costPerHour": self.cloud_provider.get_cost_per_hour_for_node_pool(pool) 
			}

			node_templates.append(node_template) 

		virtual_nodes = []  
		for template in node_templates: 
			base_type = Node(template | {"isVirtual": True}) 
			count_needed =base_type.calculate_amount_of_node_to_fit_full_workload(self.workloads)
			virtual_nodes.extend([Node(template | {"isVirtual": True, "name": f"{base_type.name}-{str(idx)}"}) for idx in range(count_needed)]) 

		self.virtual_nodes = virtual_nodes  


	def __get_pool_for_node(self, node_labels: dict) -> NodePool:  
		pool_name = self.cloud_provider.parse_node_pool_from_node_label(node_labels) 

		if pool_name: 
			for pool in self.node_pools: 
				if pool_name == pool.name: 
					return pool 

			if self.ignore_node_pool: 
				return NodePool(pool_name, pool_name) 
			
		return None

	def __check_node_pool_config(self, pool_name):  
		if len(self.optimizer_config.restrict_k8_node_pools) == 0: 
			return True 
		
		for restriction in self.optimizer_config.restrict_k8_node_pools: 
			if restriction in pool_name: 
				return True 
			
		return False 

	def __get_nodes(self) -> list[Node]:  
		""" 
		Currently, we do not access the node pools in the cluster, 
		instead we fetch the nodes that are running and use these to 
		optimize the pod assignment
		""" 
		node_list = self.v1.list_node() 
		nodes = []


		ignored_nodes = ["ip-192-168-18-172.eu-central-1.compute.internal", "ip-192-168-206-115.eu-central-1.compute.internal", "ip-192-168-48-42.eu-central-1.compute.internal"]
		for node in node_list.items:   
			node_pool = self.__get_pool_for_node(node.metadata.labels)  

			if node_pool and self.__check_node_pool_config(node_pool.name): 
				if node.metadata.name not in ignored_nodes: 
					nodes.append(Node({"name": node.metadata.name, 
						"poolname":node_pool.name, 
						"node_pool": node_pool,  
						"allocatableCPU": parse_cpu_to_m(node.status.allocatable, "cpu", 400), 
						"allocatableMemory": parse_memory_to_mi(node.status.allocatable, "memory", 400), 
						"costPerHour": self.cloud_provider.get_cost_per_hour_for_node_pool(node_pool), 
						"taints": node.spec.taints,
					}))
		print("Done loading ", str(len(nodes)), " nodes")
		self.nodes = nodes   
	
	def __node_name_exists(self, node_name): 
		for node in self.nodes: 
			if node.name == node_name: 
				return True 
		return False 

	def __get_pod_disruption_budget(self):  
		pdbs = [] 

		res = self.policy.list_pod_disruption_budget_for_all_namespaces() 

		for pdb in res.items: 
			pdbs.append(Pod_disruption_budget({"name": pdb.metadata.name, "max_unavailable": pdb.spec.max_unavailable, "min_available": pdb.spec.min_available, "selector": pdb.spec.selector}))
		
		self.pdbs = pdbs 

	def __get_vpa(self) -> list[VPA]:  
		# TODO: Query namespaces 
		vpas = [] 
		if self.optimizer_config.disabled_vpa: 
			return vpas 
		
		res = self.custom_objects.list_namespaced_custom_object(group="autoscaling.k8s.io", plural="verticalpodautoscalers", version="v1", namespace="ts") 
		for item in res["items"]: 
			vpas.append(VPA(item)) 
		
		self.vpas = vpas
	
	def __get_rs_to_deployment_mapping(self): 
		res = self.apps_v1.list_replica_set_for_all_namespaces()
		
		mapping = {}
		for item in res.items:  
			if item.metadata.name and len(item.metadata.owner_references) == 1 and item.metadata.owner_references[0].kind == "Deployment": 
				mapping[item.metadata.name] = item.metadata.owner_references[0].name
		return mapping 
	
	def __get_node_pool_selector(self, selector: dict): 
		if selector and "cloud.google.com/gke-nodepool" in selector: 
			return selector["cloud.google.com/gke-nodepool"] 
		return None  
	
	def __get_workloads(self) -> list[Workload]: 
		rs_mapping = self.__get_rs_to_deployment_mapping() 
		wls = [] 	

		ret = self.v1.list_pod_for_all_namespaces(watch=False)
		for i in ret.items: 
			containers = i.spec.containers
			cpu_req = 0 
			cpu_limit = 0
			mem_req = 0 
			mem_limit = 0

			for c in containers:  
				cpu_req += parse_cpu_to_m(c.resources.requests, "cpu", 0)  
				cpu_limit += parse_cpu_to_m(c.resources.limits, "cpu", 0) 
				mem_req += parse_memory_to_mi(c.resources.requests, "memory", 0) 
				mem_limit += parse_memory_to_mi(c.resources.limits, "memory", 0)

			is_critical_task = False  
			if i.spec.priority_class_name == "system-cluster-critical": 
				is_critical_task = True 

			wl = Workload({
				"name": i.metadata.name, 
				"cpuRequest": cpu_req,  
				"cpuLimit": cpu_limit, 
				"memoryRequest": mem_req, 
				"memoryLimit": mem_limit,
				"tolerations": i.spec.tolerations, 
				"nodeSelector": self.__get_node_pool_selector(i.spec.node_selector), 
				"currentNodeName": i.spec.node_name, 
				"labels":i.metadata.labels, 
				"namespace":i.metadata.namespace,
				"criticalWorkload": is_critical_task
			})
			
			# Move to func 
			is_daemon_set = False 
			owner_references = i.metadata.owner_references if i.metadata.owner_references is not None else [] 
			if len(owner_references) == 0: 
				print("Owner references are missing for ", wl.name)

			for owner_reference in owner_references: 
				if owner_reference.kind == "Node": 
					""" 
					The issue with these kind of services: 
					They are a daemon set but seem to behave differently here. 
					If we bootup new nodes, they will have this service as well. 
					""" 
					if "kube-proxy" in wl.name: 
						is_daemon_set = True
						found = False   

						# TODO: Clean this up and move this to function
						for deamon_set in self.daemon_sets: 
							if deamon_set.name == "kube_proxy": 
								found = True 
						if found == False:   
							wl.name = "kube_proxy"
							self.daemon_sets.append(wl)  
					else:  
						print(owner_reference) 
						raise Exception("Do not know this owner_reference")
				if owner_reference.kind == "DaemonSet":
					is_daemon_set = True
					
					# TODO: Find a simple find solution 
					# TODO: Now we are missing the real pod names that are already deployed. Does it matter? 
					found = False  
					for deamon_set in self.daemon_sets: 
						if deamon_set.name == owner_reference.name: 
							found = True 
					if found == False:  
						wl.name = owner_reference.name 
						self.daemon_sets.append(wl) 

				if owner_reference.kind == "ReplicaSet":  
					wl.replica_set_name = owner_reference.name 
					if owner_reference.name in rs_mapping:  
						wl.deployment_name = rs_mapping[owner_reference.name] 

				if owner_reference.kind == "Deployment": 
					wl.deployment_name = owner_reference.name

			if is_daemon_set == False: 
				if self.__node_name_exists(wl.current_node_name) or wl.namespace in self.optimizer_config.boot_namespaces: 
					wls.append(wl) 	 
				#print("Node not found for wl ", wl.name)


		self.workloads = wls
	
	def __get_deployments(self): 
		dps = self.apps_v1.list_deployment_for_all_namespaces()  
		deployments = [] 
		for dp in dps.items: 
			deployments.append(Deployment(dp)) 
		
		self.deployments = deployments 

	def get_latest_events(self): 
		try:  
			client.EventsV1Event.attribute_map["event_time"] = "deprecatedLastTimestamp" 
			events = self.events.list_event_for_all_namespaces(watch=False)  
			return events.items
		except Exception as e: 
			print("Coult not fetch events", e)
	
	def __sync_current_pod_utilization(self):
		pod_utilization = self.custom_objects.list_cluster_custom_object("metrics.k8s.io", "v1beta1", "pods")  
		
		for utilization in pod_utilization["items"]:  

			total_memory_utilization = 0 
			total_cpu_utilization = 0 
			
			for container in utilization["containers"]:  
				memory = parse_memory_to_mi(container["usage"], "memory", 0)  
				cpu = parse_cpu_to_m(container["usage"], "cpu", 0)  
				total_memory_utilization +=  memory if memory is not None else 0 
				total_cpu_utilization += cpu if cpu is not None else 0 
			
			for wl in self.workloads: 
				if wl.name == utilization["metadata"]["name"]:  
					# Experimental 

					if wl.cpu_request is None or total_cpu_utilization > wl.cpu_request: 
						wl.cpu_utilization = total_cpu_utilization  
						wl.cpu_request = total_cpu_utilization * 2
					
					if wl.memory_request is None or total_memory_utilization > wl.memory_request: 
						wl.memory_utilization = total_memory_utilization  
						wl.memory_request = total_memory_utilization * 2

	def prepare_boot_node(self, node): 
		self.boot_node_queue.append(node) 

	def boot_node(self, node): 
		boot_plan = {}

		if len(self.boot_node_queue) > 0: 
			for node in self.boot_node_queue: 
				if node.node_pool.provider_machine_name in boot_plan: 
					boot_plan[node.node_pool.provider_machine_name] += 1 
				else: 
					boot_plan[node.node_pool.provider_machine_name] = 1

		boot_success = False 
		if self.optimizer_config.dry_run: 
			print(boot_plan)
			print("Not booting node in dry run") 
			return  
		
		if len(boot_plan.keys()) > 0: 
			for key in boot_plan.keys(): 
				result = self.handle_node_boot_request(key, boot_plan[key])   

				# TODO: If result is success - wait for action to complete by querying cluster
				if boot_success == False and result == True:  
					boot_success = True
		
		self.boot_node_queue = []


	def check_boot_node(self, node): 
		pass 

	def __retry_add_node_to_pool(self, pool_name, size):
		operation_id = None 
		retry_count = 0 

		while retry_count < 10 and operation_id == None: 
			print(f"Trying to adjust node pool {pool_name} to size {size}") 
			if retry_count > 0: 
				print(f"Current retry {str(retry_count)}") 

			operation_id = self.cloud_provider.add_node_to_node_pool(pool_name, size)  

			retry_count += 1
			if operation_id == None: 
				time.sleep(30)  
		
		print("Checking if node added to pool")

		operation_complete = False 
		if operation_id: 
			check_operation_count = 0  

			while check_operation_count < 10 and operation_complete == False: 
				operation_complete = self.cloud_provider.check_node_added_to_pool(operation_id)  
				print(f"Operation complete {operation_complete} - retry no {check_operation_count}")
				if operation_complete == False: 
					time.sleep(15) 

		return operation_complete 
	

	def handle_node_boot_request(self, machine_name, count): 
		for node_pool in self.node_pools:   
			# For experiment purposes 
			if "ts" in node_pool.name: 
				if machine_name == node_pool.provider_machine_name: 
					current_size = 0 
					for node in self.nodes: 
						if node.node_pool.name == node_pool.name: 
							current_size += 1 
					
					return self.__retry_add_node_to_pool(node_pool.name, current_size + count)
				
		print("Could not find a matching machine")  
		return False  
	
	def add_multiple_nodes(self, configuration: dict): 
		""" 
		Add and check multiple node bootups on the 
		cloud provider in parallel
		"""  

		running_boot_operations = []  
		wait_count = 0 

		for manager_url in configuration.keys(): 
			operation = self.cloud_provider.increase_node_instance_count(manager_url, configuration[manager_url]) 
			running_boot_operations.append(operation) 
		

		while len(running_boot_operations) > 0 and wait_count < 10:  
			for op_idx, op in enumerate(running_boot_operations): 
				if op.done(): 
					print("A boot operation has completed") 
					running_boot_operations.pop(op_idx)
			
			if len(running_boot_operations) > 0: 
				time.sleep(15) 
				wait_count += 1 
		
		if len(running_boot_operations) > 0: 
			return False 
		
		return True




	def evict_pod(self, name, namespace):   
		if self.optimizer_config.dry_run: 
			print("Not evicting pod in dry run mode") 
			return 
		
		body = client.V1Eviction(metadata=client.V1ObjectMeta(name=name, namespace=namespace))

		field_manager = 'kinema' # str | fieldManager is a name associated with the actor or entity that is making these changes. The value must be less than or 128 characters long, and only contain printable characters, as defined by https://golang.org/pkg/unicode/#IsPrint. (optional)
		try:
			self.v1.create_namespaced_pod_eviction(name, namespace, body, field_manager=field_manager)
			return True 
		except Exception as e:
			print("Exception when calling CoreV1Api->create_namespaced_pod_eviction: %s\n" % e)
			return False

	def drain_node(self, node):  
		if self.optimizer_config.dry_run: 
			print("Not draining node in dry run") 
			return 
		
		self.__cordon_toggle_node(node.name, True)  
		print("Evicting pods")
		for pod in self.workloads: 
			if pod.current_node_name == node.name: 
				self.evict_pod(pod.name, pod.namespace) 
		
		print("Deleting node")
		self.delete_node(node.name)
	

	def __cordon_toggle_node(self, node_name, cordon = True):  
		if self.optimizer_config.dry_run == True: 
			print("Not cordoning node in dry run ")
			return 
		
		self.v1.patch_node(node_name, {"spec": {"unschedulable": cordon}})

	def mark_node_as_unschedulable(self, node_name): 
		self.__cordon_toggle_node(node_name, True) 
		
	def delete_node(self, node_name):  
		try: 
			self.cloud_provider.delete_node(node_name)
			return True 
		except Exception as e:  
			print("Error deleting node", node_name, e)  
			return False  
	
	def update_node_label(self, node_name, key, value):  
		try : 
			node = self.v1.read_node(node_name) 
			node.metadata.labels[key] = value 
			self.v1.patch_node(node_name, node)    
		except Exception as e: 
			print("Error: Could not label node ", node_name, e)
			print(node_name, key, value)
	
	def are_rs_stable(self):
		try:
			# Retrieve the list of ReplicaSets in the specified namespace
			resp = self.apps_v1.list_namespaced_replica_set("ts") 

			# Iterate over the ReplicaSets and check their desired and current replicas
			for rs in resp.items:   
				desired_replicas = rs.spec.replicas
				current_replicas = rs.status.replicas 
				ready_replicas = rs.status.ready_replicas

				# If desired replicas are not equal to current replicas, return False
				if desired_replicas != current_replicas or (ready_replicas is not None and desired_replicas != ready_replicas):
					print(f"{rs.metadata.name} mismatch between desired replicas {desired_replicas}, current {current_replicas} and ready {ready_replicas}")
					return False

			# All ReplicaSets have desired replicas equal to current replicas
			return True

		except Exception as e:
			print("Exception when calling AppsV1Api->list_namespaced_replica_set: %s\n" % e)
			return False




