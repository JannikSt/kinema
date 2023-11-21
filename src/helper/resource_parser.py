


def parse_cpu_to_m(config: dict, key: str, fallback_value: int):    
		if config and key in config: 
			if "m" in config[key]: 
				return int(config[key].replace("m", ""))  
			elif "n" in config[key]: 
				return int(config[key].replace("n", "")) / 1000000

		if fallback_value is not None: 
			return fallback_value 
		else: 
			return None 
		
def gb_to_mi(gb): 
	return gb * 953.674

def parse_memory_to_mi(config: dict, key: str, fallback_value: int):   
		if(config and key in config):  
			if "Ki" in config[key]:
				return int(config[key].replace("Ki", "")) / 1024
			else:  
				if "k" in config[key]: 
					return round(int(config[key].replace("k", "")) / 1048.58)
				elif "Mi" in config[key] or "M" in config[key]: 
					return int(config[key].replace("Mi", "").replace("M", ""))  
				elif "G" in config[key]: 
					return gb_to_mi(int(config[key].replace("G", "")))
				elif config[key].isnumeric(): 
					# bytes  
					return int(config[key]) / 1.049e+6 
				else: 
					print("Cannot handle ", config[key])
		
		if fallback_value is not None: 
			return fallback_value 
		else: 
			return None 