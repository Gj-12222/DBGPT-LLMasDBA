from our_argparse import args
import json
import multiprocessing as mp
from math import floor
import jsonlines
import time
import os
import asyncio

from multiagents.multiagents import MultiAgents
from multiagents.tools.metrics import database_server_conf, db
from multiagents.tools.metrics import get_workload_statistics, get_slow_queries, WORKLOAD_FILE_NAME, ANOMALY_FILE_NAME
from multiagents.utils.server import obtain_slow_queries


async def main(process_id):
    global anomaly_jsons, result_jsons

    # copy a new args
    new_args = args

    if process_id + 1 == process_num:
        # [process_id*split_size:]
        diag_ids = list(anomaly_jsons.keys())[process_id*split_size:]
    else:
        # process_id*split_size: (process_id+1)*split_size
        diag_ids = list(anomaly_jsons.keys())[process_id*split_size: (process_id+1)*split_size]

    for diag_id in diag_ids:
        if diag_id not in finished_diag_ids:
            content = anomaly_jsons[diag_id]

            # ============================= workload info =============================
            new_args.diag_id = diag_id

            # slow_queries = []
            workload_statistics = []
            # workload_sqls = ""
            # if new_args.enable_slow_query_log == True:
                # [slow queries] read from query logs
                # /var/lib/pgsql/12/data/pg_log/postgresql-Mon.log
                # slow_queries = obtain_slow_queries(database_server_conf)
                # slow_queries = content["slow_queries"] # list type
            if new_args.enable_workload_statistics_view == True:
                workload_statistics = db.obtain_historical_queries_statistics(topn = 50)
            # if new_args.enable_workload_sqls == True:
                # workload_sqls = content["workload"]

            with open(WORKLOAD_FILE_NAME, 'w') as f:
                json.dump({'workload_statistics': workload_statistics}, f)

            if "alerts" in content and content["alerts"] != []:
                new_args.alerts = content["alerts"] # possibly multiple alerts for a single anomaly
            else:
                new_args.alerts = []

            if "labels" in content and content["labels"] != []:
                new_args.labels = content["labels"]
            else:
                new_args.labels = []
            
            new_args.start_at_seconds = content["start_time"]
            new_args.end_at_seconds = content["end_time"]        
            # =======================================================================================
            # =======================================================================================

            multi_agents = MultiAgents.from_task(new_args.agent_conf_name, new_args)
            report, records = await multi_agents.run(new_args)
            
            # detailed log
            with open(reports_log_dir_name + "/diag_"+diag_id+".jsonl", "w") as f:
                json.dump(report, f, indent=4)

            with open(reports_log_dir_name + "/record_"+diag_id+".jsonl", "w") as f:
                json.dump(records, f, indent=4)

            # result logs
            result_jsons[diag_id]["diag_"+method] = report["root cause"]
            result_jsons[diag_id]["solution_"+method] = report["solutions"]

            out_file.write(str(diag_id))
            out_file.write(result_jsons[diag_id])
            out_file.write('==========================')
            print(str(diag_id), '========== ok ================')

def wrapper(i):
    asyncio.run(main(i))

# read from the anomalies with alerts. for each anomaly, 
process_num = 4
output_answer_file = "batch_testing_answers.jsonl"
result_log_prefix = "./alert_results/logs/diagnosis_results/"
log_dir_name = result_log_prefix + "2023-11-05-18-55-22-5-cases"
reports_log_dir_name = log_dir_name + "/reports"

method = "d_bot_gpt4"
finished_diag_ids = [] # finished_diag_ids = ['0', '14', '2', '25', '30', '36', '41', '49', '54', '6', '1', '15', '20', '26', '31', '37', '42', '5', '55', '60', '10', '16', '21', '27', '32', '38', '45', '50', '56', '61', '11', '17', '22', '28', '33', '39', '46', '51', '57', '7', '12', '18', '23', '29', '34', '4', '47', '52', '58', '8', '13', '19', '24', '3', '35', '40', '48', '53', '59', '9']



with open(ANOMALY_FILE_NAME, "r") as f:
    anomaly_jsons = json.load(f)

result_jsons = {}
for anomaly_id in anomaly_jsons:
    anomaly = anomaly_jsons[anomaly_id]
    alerts = anomaly["alerts"]
    alert_names = []
    for alert in alerts:
        if 'alerts' in alert:
            alert_names.append(alert['alerts'][0]['labels']['alertname'])
    result_jsons[anomaly_id] = {"labels": anomaly["labels"], 
                                "alerts": alert_names,
                                "diag_"+method: "",
                                "solution_"+method: ""}

split_size = int(floor(len(anomaly_jsons) / process_num))
out_file = jsonlines.open(log_dir_name + "/overall_diag_results.json", "a")
out_file._flush = True

if __name__=='__main__':

    if not os.path.exists(log_dir_name):
        os.makedirs(log_dir_name)

    if not os.path.exists(reports_log_dir_name):
        os.makedirs(reports_log_dir_name)
    
    with mp.Pool(processes=process_num) as pool:
        pool.map(wrapper, range(process_num))
    pool.terminate()