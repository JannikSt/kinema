

class Toleration: 
    def __init__(self, config: dict): 
        self.effect = config.effect
        self.key = config.key
        self.value = config.value

class Workload:  
    def parse_tolerations(self, config: dict): 
        if config is not None and "tolerations" in config and config["tolerations"] is not None:   
             return [Toleration(t) for t in config["tolerations"]]
        else: 
            return []  

    
    def __init__(self, config: dict): 
        self.name = config["name"]
        
        self.cpu_request = config["cpuRequest"] 
        self.cpu_limit = config["cpuLimit"] if "cpuLimit" in config else 0
        self.cpu_recommendation = None 
        self.cpu_utilization = None  

        self.memory_request = config["memoryRequest"]   
        self.memory_limit = config["memoryLimit"] if "memoryLimit" in config else 0
        self.memory_recommendation = None 
        self.memory_utilization = None 

        self.tolerations = self.parse_tolerations(config) 
        self.node_selector = config["nodeSelector"] if config is not None and "nodeSelector" in config else None 
        self.current_node_name = config["currentNodeName"] if config is not None and "currentNodeName" in config else None 
        self.labels = config["labels"] if config is not None and "labels" in config else {} 
        self.deployment_name = config["deploymentName"] if config is not None and "deploymentName" in config else {}  
        self.replica_set_name = config["replicaSetName"] if config is not None and "replicaSetName" in config else {}    
        self.namespace = config["namespace"] if config is not None and "namespace" in config else None

        self.is_critical_workload = config["criticalWorkload"] if config is not None and "criticalWorkload" in config else False  

    def get_resource_request(self, type, recommended = False, use_limit = False): 
        if(type == 'cpu'): 
            if recommended and self.cpu_recommendation: 
                return self.cpu_recommendation 
            elif use_limit: 
                return self.cpu_limit
            else: 
                return self.cpu_request 

        if(type == 'memory'):  
            if recommended and self.memory_recommendation: 
                return self.memory_recommendation  
            elif use_limit: 
                return self.memory_limit
            else: 
                return self.memory_request

        return None 
    
    def apply_request_recommendation(self): 
        if self.cpu_recommendation: 
            self.cpu_request = self.cpu_recommendation 
            self.cpu_recommendation = None  
        
        if self.memory_recommendation: 
            self.memory_request = self.memory_recommendation
            self.memory_recommendation = None 
            
    def has_recommendation(self): 
        return self.memory_recommendation != None and self.memory_recommendation != 0 and self.cpu_recommendation != None and self.cpu_recommendation != 0
    
    @staticmethod
    def get_total_request_for_workloads(workloads: list, resourceType: str):  
        value = 0
        for wl in workloads:  
            if resourceType == "cpu": 
                value += wl.cpu_request 
            else: 
                value += wl.memory_request 

        return value

