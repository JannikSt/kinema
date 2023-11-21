import matplotlib.pyplot as plt 
from matplotlib.pyplot import get_cmap
import scienceplots 

class Stat_collector: 
    
	def __init__(self):
		self.stats = { 
			"iteration": [],
			"cost_per_hour": [], 
			"pods_to_reschedule": [], 
			"virtual_node_count": [], 
			"drain_node_count": [],
			"iteration_duration": [], 
			"allocated_cpu": [],  
			"allocated_memory": [], 
			"total_node_count": [], 
			"allocatable_cpu": [], 
			"allocatable_memory": [],
			"total_unused_resources": [], 
			"workload_count": []
		} 
	
	# Stored metrics 
	dip_bug_separate_goal_for_mem_cpu =  {'iteration': [-1, 0, 1, 2, 3, 4, 5], 'cost_per_hour': [1.97, 2.2099379999999993, 1.5, 1.43, 1.43, 1.43, 1.43], 'pods_to_reschedule': [0, 0, 30.0, 8.0, 0.0, 0.0, 0.0], 'virtual_node_count': [0, 2.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'iteration_duration': [None, 17.198323249816895, 1.0210061073303223, 26.516257762908936, 24.012928009033203, 24.949172019958496, 23.487866163253784], 'allocated_cpu': [31352, 27614, 11472, 19291, 26825, 26825, 26825], 'allocated_memory': [31352, 27614, 11472, 19291, 26825, 26825, 26825], 'total_node_count': [20, 22, 12, 11, 11, 11, 11], 'allocatable_cpu': [32740, 38590.0, 29190.0, 27260.0, 27260.0, 27260.0, 27260.0], 'allocatable_memory': [107437.4453125, 121647.19262695312, 93521.98168945312, 92091.47021484375, 92091.47021484375, 92091.47021484375, 92091.47021484375]}
	# actually shows that there is an improvement in cost per hour 
	dip_bug_common_goal_for_mem_cpu = {'iteration': [-1, 0, 1, 2, 3, 4, 5], 'cost_per_hour': [1.97, 1.26, 1.26, 1.26, 1.26, 1.26, 1.26], 'pods_to_reschedule': [0, 22.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'virtual_node_count': [0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'iteration_duration': [None, 3.9417991638183594, 2.092567205429077, 2.144191265106201, 2.111017942428589, 2.0992650985717773, 2.0936291217803955], 'allocated_cpu': [26552, 6612, 22792, 22792, 22792, 22792, 22792], 'allocated_memory': [26552, 6612, 22792, 22792, 22792, 22792, 22792], 'total_node_count': [20, 10, 10, 10, 10, 10, 10], 'allocatable_cpu': [32740, 23340, 23340, 23340, 23340, 23340, 23340], 'allocatable_memory': [107437.4453125, 79312.234375, 79312.234375, 79312.234375, 79312.234375, 79312.234375, 79312.234375]}

	def __ensure_have_data(self, key): 
		return len(self.stats[key]) == len(self.stats["iteration"]) 

	def __get_current_iteration(self): 
		return self.stats["iteration"][len(self.stats["iteration"])-1]

	def collect_stat(self, key, value):  
		try : 
			if key in self.stats:  
				if self.__ensure_have_data(key) == False or key == 'iteration': 
					self.stats[key].append(value)   
				else: 
					self.stats[key][self.__get_current_iteration()] = value  
		except Exception as e: 
			print("Error collecting stats", e) 
				
	def increment_stat(self, key): 
		if key in self.stats:  
			current_iteration_item_count = len(self.stats["iteration"])
			current_iteration = current_iteration_item_count -1

			if len(self.stats[key]) == current_iteration_item_count: 
				self.stats[key][current_iteration] += 1 
			else: 
				self.stats[key].append(1) 
 
	def collect_stats(self, data: dict):    
		for key in data.keys():  
			self.collect_stat(key, data[key])  
	
	def get_current_stat(self, key): 
		if key not in self.stats:   
			raise Exception("Key is not tracked") 
		
		current_iteration_item_count = len(self.stats["iteration"])
		current_iteration = current_iteration_item_count -1
		if len(self.stats[key]) == current_iteration_item_count: 
			return self.stats[key][current_iteration]
		else: 
			raise Exception("No tracking data found")

	
	def demo(self): 
		self.stats = {'iteration': [-1, 0, 1, 2, 3, 4, 5], 'cost_per_hour': [1.97, 2.2099379999999993, 1.5, 1.43, 1.43, 1.43, 1.43], 'pods_to_reschedule': [0, 0, 30.0, 8.0, 0.0, 0.0, 0.0], 'virtual_node_count': [0, 2.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'iteration_duration': [None, 17.198323249816895, 1.0210061073303223, 26.516257762908936, 24.012928009033203, 24.949172019958496, 23.487866163253784], 'allocated_cpu': [31352, 27614, 11472, 19291, 26825, 26825, 26825], 'allocated_memory': [31352, 27614, 11472, 19291, 26825, 26825, 26825], 'total_node_count': [20, 22, 12, 11, 11, 11, 11], 'allocatable_cpu': [32740, 38590.0, 29190.0, 27260.0, 27260.0, 27260.0, 27260.0], 'allocatable_memory': [107437.4453125, 121647.19262695312, 93521.98168945312, 92091.47021484375, 92091.47021484375, 92091.47021484375, 92091.47021484375]}
		self.plot() 
	
	def close_iteration(self): 
		""" 
		If we do not have a value for the current iteration, 
		set None 
		""" 
		for key in self.stats.keys():  
			if(len(self.stats[key])) < len(self.stats["iteration"]): 
				self.stats[key].append(0)  
			# Debug
			print(key, self.stats[key][len(self.stats["iteration"])-1])

	def plot(self): 
		print(self.stats) 

		plt.style.use('science')
		fig, axs = plt.subplots(7, sharex=True)   

		axs[0].set_prop_cycle(color=get_cmap("Accent").colors)
		axs[1].set_prop_cycle(color=get_cmap("Paired").colors)
		axs[2].set_prop_cycle(color=get_cmap("tab10").colors)

		axs[0].plot(self.stats["iteration"], self.stats["cost_per_hour"], label="USD per hour") 
		axs[0].legend()

		axs[1].plot(self.stats["iteration"], self.stats["pods_to_reschedule"], label="pods to reschedule")   
		
		if self.__ensure_have_data("drain_node_count"): 
			axs[1].plot(self.stats["iteration"], self.stats["drain_node_count"], label="drain node count")
		
		# axs[1].plot(self.stats["iteration"], self.stats["iteration_duration"], label="iteration duration (s)", color='y')  
		axs[1].legend()

		#axs[2].plot(self.stats["iteration"], self.stats["avg_cpu_utilization"], label="% Alloc. cpu utilized ", color='b')  
		#axs[2].plot(self.stats["iteration"], self.stats["avg_memory_utilization"], label="% Alloc. memory utilized", color='g')  
		#axs[2].plot(self.stats["iteration"], self.stats["total_node_count"], label="Node count", color='r')  
		#axs[2].legend(bbox_to_anchor=(0, 1.02, 1, 0.2), loc="lower left",
        #        mode="expand", borderaxespad=0, ncol=3)
		
		if self.__ensure_have_data("allocated_cpu"): 
			axs[2].plot(self.stats["iteration"], self.stats["allocated_cpu"], label="Allocated cpu")  
		if self.__ensure_have_data("allocatable_cpu"): 
			axs[2].plot(self.stats["iteration"], self.stats["allocatable_cpu"], label="Allocatable cpu")   
		axs[2].legend()

		if self.__ensure_have_data("allocated_memory"): 
			axs[3].plot(self.stats["iteration"], self.stats["allocated_memory"], label="Allocated Memory")  
		if self.__ensure_have_data("allocatable_memory"): 
			axs[3].plot(self.stats["iteration"], self.stats["allocatable_memory"], label="Allocatable Memory")    
		axs[3].legend()
 
		axs[4].plot(self.stats["iteration"], self.stats["total_unused_resources"], label="Total unused resources") 
		unused_cpu = [] 
		unused_memory = [] 
		for it in self.stats["iteration"]: 
			unused_cpu.append(self.stats["allocatable_cpu"][it]-self.stats["allocatable_cpu"][it]) 
			unused_memory.append(self.stats["allocatable_memory"][it]-self.stats["allocated_memory"][it]) 
		axs[4].plot(self.stats["iteration"], unused_cpu, label="Total unused cpu") 
		axs[4].plot(self.stats["iteration"], unused_memory, label="Total unused memory") 
		axs[4].legend()
		
		if self.__ensure_have_data("total_node_count"):  
			axs[5].plot(self.stats["iteration"], self.stats["total_node_count"], label="Nodecount")   
		
		if self.__ensure_have_data("workload_count"):  
			axs[5].plot(self.stats["iteration"], self.stats["workload_count"], label="Workload count")   

		axs[5].legend() 

		axs[6].plot(self.stats["iteration"], self.stats["virtual_node_count"], label="new nodes to boot")   
		axs[6].legend()

		plt.xticks(self.stats["iteration"])

		plt.show()