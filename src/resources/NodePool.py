
class NodePool: 

	def __init__(self, name, provider_machine_name, **kwargs): 
		self.name = name 
		self.provider_machine_name = provider_machine_name 
		self.manager_url = kwargs.get('manager_url', None)
	
