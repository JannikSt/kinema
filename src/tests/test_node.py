import unittest 
from resources.node import Node

class Test_Node(unittest.TestCase):  
    
	def test_copy(self): 
		
		node_1 = Node({ 
			"name": "firstnode", 
			"poolname":"ts",
			"allocatableCPU":100,
			"allocatableMemory":200,
			"costPerHour": 1.4
		}) 

		node_2 = node_1.copy()   
		assert(node_1.name == "firstnode") 
		assert(node_2.name == "firstnode") 

		node_2.name = "Node2"  
		assert(node_1.name == "firstnode") 
		assert(node_2.name == "Node2")

    