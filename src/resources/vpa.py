from helper.resource_parser import parse_cpu_to_m, parse_memory_to_mi
from resources.workload import Workload 

class ContainerRecommendation: 

	def parse_bound(self, config: dict): 
		if config is None: 
			return None 
		
		return { 
			"cpu": parse_cpu_to_m(config, "cpu", 0), 
			"memory": parse_memory_to_mi(config, "memory", 0)
		}

	def __init__(self, config: dict): 
		self.container_name = config["containerName"] 
		self.lower_bound = self.parse_bound(config["lowerBound"]) 
		self.target= self.parse_bound(config["target"])  
		self.uncapped_target = self.parse_bound(config["uncappedTarget"])  
		self.upper_bound = self.parse_bound(config["upperBound"])  

class Recommendation: 
	def parse_container_recommendations(self, config: dict): 
		if 'containerRecommendations' not in config: 
			return [] 

		recommendations = []
		for recommendation in config["containerRecommendations"]: 
			recommendations.append(ContainerRecommendation(recommendation))
		return recommendations 

	def __init__(self, config: dict): 
		self.container_recommendations = self.parse_container_recommendations(config) 
	
	def get_pod_recommendations(self, **kwargs): 
		# MVP only focus on lower bound recommendation 
		cpu_recommendation = 0
		memory_recommendation = 0 

		attribute = kwargs.get('attribute', 'target')
	
		for container in self.container_recommendations:  
			if container and hasattr(container, attribute) and "cpu" in getattr(container, attribute): 
				cpu_recommendation += getattr(container, attribute)["cpu"] 
			if container and hasattr(container, attribute) and "memory" in getattr(container, attribute): 
				memory_recommendation += getattr(container, attribute)["memory"]
		
		return { 
			"cpu": cpu_recommendation, 
			"memory": memory_recommendation
		}
			


class VPA: 
    
	def __init__(self, config: dict): 
		self.name = config["metadata"]["name"] 
		self.targetRef = config["spec"]["targetRef"] 
		self.recommendation = Recommendation(config["status"]["recommendation"]) 

	def check_if_vpa_exist_for_workload(self, workload: Workload):   
		if workload.deployment_name and self.targetRef["kind"] == "Deployment": 
			if self.targetRef["name"] == workload.deployment_name: 
				return True
		return False  
	
	def apply_vpa_recommendations_to_workloads(self, workloads: list[Workload]): 
		for wl in workloads:  
			wpa_exists = self.check_if_vpa_exist_for_workload(wl) 
			if wpa_exists: 
				recommendation = self.recommendation.get_pod_recommendations() 
				
				if recommendation["cpu"] != 0 and wl.cpu_request != recommendation["cpu"] :
					wl.cpu_recommendation = recommendation["cpu"]   

				if recommendation["memory"] != 0 and wl.memory_request != recommendation["memory"]:   
					wl.memory_recommendation = recommendation["memory"] 