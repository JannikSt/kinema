from prometheus_api_client import PrometheusConnect
import pandas as pd
from sklearn.linear_model import LinearRegression
from datetime import datetime, timedelta 
import numpy as np
import matplotlib.pyplot as plt  
import time

from resources.Config import Config 
from helper.resource_parser import parse_cpu_to_m, parse_memory_to_mi 

class UtilizationPredictor:
	def __init__(self, config = Config()):
		self.prometheus = PrometheusConnect(url=config.prometheus_url)  
		self.config = config 	

	def apply_recommendation_to_container_request(self, container_name, pod_names: list[str], initial_requests: dict):
		cpu_suggestion = self.__query_cpu_metrics(pod_names, container_name)
		memory_suggestion = self.__query_memory_metrics(pod_names, container_name)

		if cpu_suggestion == False or memory_suggestion == False: 
			return initial_requests 
	

		new_resource_requests = { 
			'cpu': f"{str(round(self.__adjust_value(parse_cpu_to_m(initial_requests, 'cpu', 0), cpu_suggestion, self.config.resource_adjustment_rate)))}m", 
			'memory': f"{str(round(self.__adjust_value(parse_memory_to_mi(initial_requests, 'memory', 0), memory_suggestion, self.config.resource_adjustment_rate)))}Mi"
		}
		print(f"Recommendation for container {container_name} > cpu change from "+initial_requests["cpu"]+" > "+new_resource_requests["cpu"]) 

		return new_resource_requests
	
	def __adjust_value(self, initial_value, recommendation, alpha): 
		initial_value = float(initial_value)
		recommendation = float(recommendation)  

		adjusted_value = initial_value + alpha * (recommendation - initial_value) 
		return max(adjusted_value, 1)  
	
	def __query_cpu_metrics(self, pod_names, container_name, learning_tf = 5, **kwargs): 
		try : 
			now = pd.Timestamp.now() 

			pod_filter = "|".join(pod_names) 
			timezone_offset = kwargs.get('tz_offset', 120)
			start_time = now - pd.Timedelta(minutes=timezone_offset) - pd.Timedelta(minutes=learning_tf)
			end_time = now - pd.Timedelta(minutes=timezone_offset)

			cpu_query = f'avg(sum(rate(container_cpu_usage_seconds_total{{pod=~"{pod_filter}", container="{container_name}", namespace="ts"}}[1m])) by (pod) * 1000)' 
			cpu_metrics = self.prometheus.custom_query_range(query=cpu_query, start_time=start_time, end_time=end_time, step='1m')

			if len(cpu_metrics) == 0: 
				return False
			
			timestamps = [pd.Timestamp.fromtimestamp(int(item[0])) for item in cpu_metrics[0]['values']]
			cpu_values = [float(item[1]) for item in cpu_metrics[0]['values']]

			cpu_df = pd.DataFrame({'timestamp': timestamps, 'cpu_usage': cpu_values})  

			if(len(cpu_df) < learning_tf):  
				# print("Not enough cpu data to predict load") 
				return False  
		
			X = cpu_df.index.values.reshape(-1, 1) 
			y = cpu_df['cpu_usage'].values

			cpu_model = LinearRegression()
			cpu_model.fit(X, y)
			
			last_index = X[-1][0]

			extended_X = np.vstack([X, np.arange(last_index + 1, last_index + 16).reshape(-1, 1)]) 

			next_values = cpu_model.predict(extended_X[-15:]) 
			return next_values.mean()   
		
		except Exception as e: 
			print("Error predicting cpu utilization", e) 
			return False 
	
	def __query_memory_metrics(self, pod_names, container_name, learning_tf=5, **kwargs): 
		try: 
			now = pd.Timestamp.now()

			timezone_offset = kwargs.get('tz_offset', 120)
			start_time = now - pd.Timedelta(minutes=timezone_offset) - pd.Timedelta(minutes=learning_tf)
			end_time = now - pd.Timedelta(minutes=timezone_offset)

			pod_filter = "|".join(pod_names) 
			memory_query = f'avg(sum(container_memory_usage_bytes{{container="{container_name}", pod=~"{pod_filter}", namespace="ts"}}) by (pod))'
			memory_metrics = self.prometheus.custom_query_range(query=memory_query, start_time=start_time, end_time=end_time, step='1m')

			if len(memory_metrics) == 0: 
				return False
			timestamps = [pd.Timestamp.fromtimestamp(int(item[0])) for item in memory_metrics[0]['values']]
			memory_values = [float(item[1]) / 1024**2 for item in memory_metrics[0]['values']]

			memory_df = pd.DataFrame({'timestamp': timestamps, 'memory_usage': memory_values})
			if(len(memory_df) < learning_tf):  
				# print("Not enough memory data to predict load") 
				return False   
			
			X = memory_df.index.values.reshape(-1, 1)
			y = memory_df['memory_usage'].values

			memory_model = LinearRegression()
			memory_model.fit(X, y)

			last_index = X[-1][0]

			extended_X = np.vstack([X, np.arange(last_index + 1, last_index + 16).reshape(-1, 1)])

			next_values = memory_model.predict(extended_X[-15:]) 

			return next_values.mean() 
		
		except Exception as e: 
			print("Error predicting memory utilization", e) 
			return False 
	
	def predict_stability(self, **kwargs): 
		try: 
			hpa_query = 'avg(kube_horizontalpodautoscaler_status_desired_replicas{namespace="ts"})'
			rs_query = 'avg(kube_replicaset_status_ready_replicas{namespace="ts"})'

			now = pd.Timestamp.now()

			stability_window = kwargs.get('stability_window', 45)
			timezone_offset = kwargs.get('tz_offset', 120)
			start_time = now - pd.Timedelta(minutes=timezone_offset) - pd.Timedelta(seconds=stability_window)
			end_time = now - pd.Timedelta(minutes=timezone_offset)

			hpa_data = self.prometheus.custom_query_range(query=hpa_query, start_time=start_time, end_time=end_time, step="15s")
			rs_data = self.prometheus.custom_query_range(query=rs_query, start_time=start_time, end_time=end_time, step="15s")

			# Check if changes have been stable for the last 5 minutes
			hpa_stable = all(data[1] == hpa_data[0]['values'][-1][1] for data in hpa_data[0]['values'][:-1]) 
			
			rs_stable = all(data[1] == rs_data[0]['values'][-1][1] for data in rs_data[0]['values'][:-1])
		

			# Return True if changes are stable for the last 5 minutes
			return hpa_stable and rs_stable 
		except Exception as e:
			print("Could not evaluate stability", e) 
			return False 
