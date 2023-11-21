
from kubernetes import client
from copy import copy 

class Deployment: 

	def __init__(self, deployment: client.V1Deployment): 
		self.name = deployment.metadata.name 
		self.namespace = deployment.metadata.namespace 
		self.full_deployment = deployment
	
	def adjust_node_affinity(self, key: str, value: str, app_client: client.AppsV1Api):  
		template = self.full_deployment.spec.template  
		affinity = template.spec.affinity 
		if affinity is None:
			template.spec.affinity  = client.V1Affinity()

		node_affinity = template.spec.affinity.node_affinity

		# Check if nodeSelectorTerms exist and create a new one if not
		if node_affinity is None:
			template.spec.affinity.node_affinity = client.V1NodeAffinity()
		
		preferred_during_scheduling_ignored_during_execution = template.spec.affinity.node_affinity.preferred_during_scheduling_ignored_during_execution
		
		# Create a new NodeSelectorRequirement for the label
		new_requirement = client.V1NodeSelectorRequirement(
			key=key,
			operator="In",
			values=[value]
		) 
	
		node_selector_term = client.V1NodeSelectorTerm(match_expressions=[new_requirement]) 

		# Append the new requirement to the existing requirements
		if preferred_during_scheduling_ignored_during_execution is None or len(preferred_during_scheduling_ignored_during_execution) == 0:
			preferred_during_scheduling_ignored_during_execution = [client.V1PreferredSchedulingTerm(preference=node_selector_term, weight=100)]
		else:   
			if len(preferred_during_scheduling_ignored_during_execution) > 0:   
				preference_found = False  

				for p in preferred_during_scheduling_ignored_during_execution: 
					for expression in p.preference.match_expressions:
						if expression.key == key:  
							preference_found = True 
							expression.values = [value] 
				
				if preference_found == False: 
					preferred_during_scheduling_ignored_during_execution.append(client.V1PreferredSchedulingTerm(preference=node_selector_term, weight=100))

		
		# Set the updated nodeAffinity to the pod template  
		template.spec.affinity.node_affinity.preferred_during_scheduling_ignored_during_execution = preferred_during_scheduling_ignored_during_execution

		self.full_deployment.spec.template = template

		# Update the Deployment with the updated pod template a
		response = app_client.patch_namespaced_deployment(
			name=self.name,
			namespace=self.namespace,
			body=self.full_deployment
		) 

		self.full_deployment = response 

	

		