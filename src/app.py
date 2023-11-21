import time 
import traceback

from resources.KubernetesCluster import KubernetesCluster
from resources.cloud_provider.google_cloud.GoogleCloud import GoogleCloud
from resources.Config import Config  

from resources.node.Node import Node, calculate_hour_price_for_node_list
from resources.workload import Workload

from action_manager.ActionManager import ActionManager
from action_manager.ClusterAction import ClusterAction 
from action_manager.ClusterActionTypes import ClusterActionTypes 

from rescheduler.Rescheduler import Rescheduler

from model.Model import Model

from helper.stat_collector import Stat_collector 

# os.environ['GRB_LICENSE_FILE'] = os.getcwd() + "/license/gurobi.lic"

# TODO: Set config and cloud env here
config = Config(dry_run=True, use_model_timelimit=False)
gCloud = GoogleCloud("cluster_name", "cluster_region", "project_id")  

k8 = KubernetesCluster(gCloud, config=config)  

k8.sync()


def kinema_iteration(iteration: int, workloads: list[Workload], nodes: list[Node], stat_collector: Stat_collector):  
        initial_hour_price = calculate_hour_price_for_node_list(nodes)   
        initial_model_k8_nodes = nodes 
        if len(initial_model_k8_nodes) == 0 and len(workloads) == 0: 
            print("Nothing to check") 
            return

        vpas = k8.vpas
        pdbs = []
        virtual_nodes = k8.virtual_nodes 
 
        for vpa in vpas:  
            vpa.apply_vpa_recommendations_to_workloads(workloads) 

        """ 
        Create an optimal state of the cluster 
        """
        model = Model(workloads, initial_model_k8_nodes, virtual_nodes, pdbs, iteration, stat_collector, config, k8)
        optimized_workloads, optimized_k8_nodes, virtual_node_bootup = model.run_optimization()  
        stat_collector.close_iteration()  

        if iteration == 0:  
            """ 
            The initial iteration is only used to collect the starting point of the cluster
            """
            print("Initial iteration done") 
            return workloads, nodes
        
        """ 
        Decision: Should we take actions to full fill the optimal model state or should we wait and calculate a new 
        optimal state after a timeout? 
        
        Take Action: 
        - No workload or node changes in cluster since calculation start 
        - Objective improvement is x % better than current state 

        No action: 
        - Objective improvement is not better 
        - Workload / Node changes happened while calculating a new optimal state
        - Reaching the next optimal cluster state would take too long (too many expected change)
        """

        for node in optimized_k8_nodes: 
            print(node.node_pool.provider_machine_name) 

        execute_optimization = False    
        optimized_hour_price = calculate_hour_price_for_node_list(optimized_k8_nodes)  
        relative_optimization = (initial_hour_price - optimized_hour_price) / initial_hour_price
        #TODO: Move to non fixed 
        expected_optimization = 0.05

        if relative_optimization >= expected_optimization: 
            execute_optimization = True  
        print("Checking change in cluster")
        # time.sleep(15)
        """  
        Stable state evaluation
        """
        k8.sync()   
        # TODO: Check if we even have workloads
        rel_node_change = abs((len(initial_model_k8_nodes) - len(k8.nodes)) / len(initial_model_k8_nodes))  
        rel_workload_change = abs((len(workloads) - len(k8.workloads)) / len(workloads))
        print("Rel node change", rel_node_change) 
        print("Rel workload change", rel_workload_change) 
        if rel_node_change + rel_workload_change > 0.1: 
            print("Too many changes since start of the optimization")
            execute_optimization = False 

        print("Initial hour price", initial_hour_price) 
        print("Optimized hour price", calculate_hour_price_for_node_list(optimized_k8_nodes))
        print("Optimization", relative_optimization) 

        if execute_optimization == False: 
            print("Not executing optimization plan - Returning")
            return workloads, initial_model_k8_nodes
        
        print("Preparing actions to take")

        """ 
        Take all necessary actions to reach this next optimal state 
        - Start to boot nodes 
        - Cordon workloads 
        - Reschedule workloads - with readiness check in mind 
        """
        rescheduler = Rescheduler(k8, optimized_k8_nodes, initial_model_k8_nodes, config=config) 
        rescheduler.execute()

        """ 
        Return for simulations 
        This is only used if we are doing a dryrun 
        """
        final_nodes = optimized_k8_nodes 
        if config.dry_run == True: 
            for node in final_nodes: 
                node.isVirtual = False 

        return optimized_workloads, final_nodes 

def run():  
    stat_collector = Stat_collector()
    current_iteration = 0
    while True:   

        if config.dry_run != True or current_iteration == 0:  
            k8.sync() 
            workloads = k8.workloads   
            nodes = k8.nodes   

        start_new_iteration = True 

        if k8.are_rs_stable() == False: 
            start_new_iteration = False 
            print("RS are not stable, not starting a new iteration") 

        if start_new_iteration == True: 
            try: 
                print("Iteration", current_iteration)
                workloads, nodes =  kinema_iteration(current_iteration, workloads, nodes,stat_collector)
                print("Workloop iteration done")
            except Exception as e:  
                print("Workload run failed", str(e)); 
                traceback.print_exc(e) 

        current_iteration += 1
        if current_iteration != 0:
            time.sleep(20) 

run()
    
		
      
