
import random
import string 

def random_string(len: int): 
	return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(len))