import inspect
import pdb
import random
import sys

class APICaller:

    def __init__(self):
        self.functions = {}
    
    def register_function(self, func_name, params, func):
        self.functions[func_name] = {"func": func, "desc": params}
    
    def call_function(self, func_name, *args, **kwargs):
        if func_name in self.functions:
            func = self.functions[func_name]["func"]
            return func(*args, **kwargs)
        else:
            print(f"Function '{func_name}' not registered.")

            return None

def get_function_parameters(func):
    if sys.version_info >= (3, 10):
        signature = inspect.signature(func)
        return list(signature.parameters.keys())
    else:
        signature = inspect.signature(func)
        parameters = signature.parameters.values()
        return [param.name for param in parameters]


def register_functions_from_module(module, caller, max_api_num):
    members = inspect.getmembers(module, inspect.isfunction)

    # 从members中随机选择前max_api_num个函数（如果数量不足则选择全部）
    # if len(members) > max_api_num:
    #     members = random.sample(members, max_api_num)

    api_cnt = 0
    necessary_names = ["match_diagnose_knowledge", "obtain_start_and_end_time_of_anomaly", "whether_is_abnormal_metric"]
    for member in members:
        if len(member) == 2:
            name, func = member
        else:
            name, _, func = member

        if func.__module__ == module.__name__:
            if name not in necessary_names:
                api_cnt = api_cnt + 1
                        
            params = get_function_parameters(func)
            caller.register_function(name, params, func)
            
            if api_cnt >= max_api_num:
                break