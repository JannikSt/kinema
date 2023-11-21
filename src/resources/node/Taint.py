from resources.workload import Workload

class Taint: 
   def __init__(self, config: dict): 
         self.effect = config.effect
         self.key= config.key
         self.value= config.value

   def can_workload_tolerate_taint(self, workload: Workload): 
      if len(workload.tolerations) == 0: 
          return False 
      
      for toleration in workload.tolerations: 
            if toleration.key == self.key and toleration.value == self.value: 
                return True

      return False