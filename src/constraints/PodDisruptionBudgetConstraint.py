from resources.pod_disruption_budget import Pod_disruption_budget 
from resources.workload import Workload  
from resources.WorkloadAssignment import WorkloadAssignment
import gurobipy as gp  

class PodDisruptionBudgetConstraint: 

	def __init__(self, model, pdbs: list[Pod_disruption_budget], workloads: list[Workload], workload_assignments: WorkloadAssignment, reschedule_vars, apply_vpa_recommendation_vars): 
		self.model = model
		self.pdbs = pdbs 
		self.workloads = workloads 
		self.workload_assignments = workload_assignments    
		self.apply_vpa_recommendation_vars = apply_vpa_recommendation_vars 

		""" 
		Vars originate in the Reschedule Constraint 
		For a workload at index x the reschedule_vars[x] binary 
		indicates if the workload is rescheduled onto another node 
		"""
		self.reschedule_vars = reschedule_vars
	
		self.setup_constraints()
 

	def match_pdb_label_to_workloads(self, selector: dict): 
		workload_indices = [] 

		for wl_index, wl in enumerate(self.workloads):
			match = False 
			for key in selector: 
				if wl.labels and key in wl.labels and wl.labels[key] == selector[key]: 
					match = True 
				else: 
					match = False 
			if match is True: 
				workload_indices.append(wl_index)  
			
		return workload_indices 

	def create_pdb_constraints(self, pdb: Pod_disruption_budget):  
		
		matching_workload_idxs = self.match_pdb_label_to_workloads(pdb.selector.match_labels) 

		if(pdb.max_unavailable is not None): 
			print("Handling max unavailable constr.") 
			# TODO 

		if(pdb.min_available is not None): 
			matching_reschedule_vars = [] 
			for workload_idx in matching_workload_idxs:  
				matching_reschedule_vars.append(self.reschedule_vars[workload_idx])  

			min_available_value = 0 
			if isinstance(pdb.min_available, str):  
				if "%" in pdb.min_available: 
					percentage = int(pdb.min_available.replace("%", ""))  
					min_available_value = round(len(matching_workload_idxs) * (percentage / 100)) 
			else: 
				min_available_value = pdb.min_available


			if len(matching_reschedule_vars) > 0: 
				self.model.addConstr(len(matching_workload_idxs) - gp.quicksum(matching_reschedule_vars) >= min_available_value)


	def setup_constraints(self): 
		for pdb in self.pdbs: 
			self.create_pdb_constraints(pdb) 


