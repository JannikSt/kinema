


class ProductCatalog: 

	def __init__(self): 
		self.machines = self.fetch_predefined_machines() 

		self.pre_package_pricing = { 
			"usd_v_cpu_per_hour": 0.028103, 
			"usd_gb_memory_per_hour": 0.003766  
		}

	def calc_usd_per_hour(self, cpu_count, mem_count): 
		return cpu_count * self.pre_package_pricing["usd_v_cpu_per_hour"] + mem_count * self.pre_package_pricing["usd_gb_memory_per_hour"] 

	def get_config_for_package_name(self, name): 
		for machine in self.machines: 
			if machine["name"] == name: 
				return machine 
		return None 

	def get_price_for_machine_name(self, machine_name):  
		config = self.get_config_for_package_name(machine_name) 
		return self.calc_usd_per_hour(config["vcpu"], config["gbMemory"]) if config else None 
  

	def fetch_predefined_machines(self): 
		return [  
		{
			"name":"e2-micro",
			"vcpu":2,
			"gbMemory":1,  
			"sharedCore": True
		}, 
		{
			"name":"e2-small",
			"vcpu":2,
			"gbMemory":2, 
			"sharedCore": True
		},
		{
			"name":"e2-medium",
			"vcpu":2,
			"gbMemory":4,  
			"sharedCore": True
		},
		{
			"name":"e2-standard-2",
			"vcpu":2,
			"gbMemory":8, 
		}, 
		{
			"name":"e2-standard-4",
			"vcpu":4,
			"gbMemory":16, 
		}, 
		{
			"name":"e2-standard-8",
			"vcpu":8,
			"gbMemory":32, 
		},
		{
			"name":"e2-standard-16",
			"vcpu":16,
			"gbMemory":64, 
		}, 
		{
			"name":"e2-highcpu-2",
			"vcpu":2,
			"gbMemory":2, 
		}, 
		{
			"name":"e2-highcpu-4",
			"vcpu":4,
			"gbMemory":4, 
		},
		{
			"name":"e2-highcpu-8",
			"vcpu":8,
			"gbMemory":8, 
		},
		{
			"name":"e2-highcpu-16",
			"vcpu":16,
			"gbMemory":16, 
		}, 
		{
			"name":"e2-highcpu-32",
			"vcpu":32,
			"gbMemory":32, 
		}, 
		{
			"name":"e2-highmem-2",
			"vcpu":2,
			"gbMemory":16, 
		}, 
		{
			"name":"e2-highmem-4",
			"vcpu":4,
			"gbMemory":32, 
		}, 
		{
			"name":"e2-highmem-8",
			"vcpu":8,
			"gbMemory":64, 
		}, 
		{
			"name":"e2-highmem-16",
			"vcpu":16,
			"gbMemory":128, 
		}, 
	]