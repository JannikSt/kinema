


class Pod_disruption_budget: 
    
	def __init__(self, config):  
		self.name = config["name"]
		self.max_unavailable = config["max_unavailable"] 
		self.min_available = config["min_available"] 
		self.selector = config["selector"]