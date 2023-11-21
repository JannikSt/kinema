run_tests: 
	python3 -m unittest tests/test_node.py 
	python3 -m unittest tests/test_workload_assignment.py
	python3 -m unittest tests/test_resource_constraint.py  
actiontest: 
	python3 -m unittest tests/test_action_manager.py  
run_cloud_test: 
	python3 -m unittest tests/test_nodepool_cloud_provider.py
run: 
	python3 app.py