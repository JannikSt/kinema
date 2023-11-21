import enum 

class ClusterActionTypes(enum.Enum):  
    # boot up a new node 
    BOOT = "boot"  
    # reschedule a pod 
    RESCHEDULE  = "reschedule"  
    # drain a node 
    DRAIN = "drain"