import argparse
import json
import os
import copy
import pandas as pd
from utils import download_json, format_node, find_node_by_path
import logging
import datetime

# 定义系统提示信息和模板
prompt_system = '''
# CONTEXT

You are an autonomous intelligent agent tasked with navigating a web browser to accomplish various web-based tasks. Your success depends on effectively utilizing the specific actions available to you. Below is the information and guidance you will have during the task:

## TASK INFORMATION

1. **User's Objective**: The goal you are tasked to achieve.  
2. **Current Web Page's Accessibility Tree**: A simplified representation of the webpage, providing key information about its elements.  
3. **Current Web Page's URL**: The URL of the page you are currently viewing.  
4. **Previous Action List**: A record of all the actions you have performed so far, useful for tracking your progress.  

## AVAILABLE ACTIONS

### 1. **Page Operation Actions**
- click [id]: Click on a webpage element identified by its id.  
- type [id][content]: Type content into the field with the specified id.  
- copy [id]: Copy the content of an element identified by its id.  
- paste [id]: Paste previously copied content into a field identified by its id.  
- cache [id]: Cache the information or value from the element with the specified id for later use.  
- hover [id]: Hover over an element identified by its id.  
- press_enter: Simulate pressing the "Enter" key.  
- double_click [id]: Perform a double click on the element identified by its id.  
- right_click [id]: Perform a right-click on the element identified by its id.  
- select [id]: Select text within an element identified by its id.  

### 2. **Navigation Actions**
- back: Return to the previously viewed page.  

### 3. **Completion Action**
- stop [answer]: Use this action when you believe the task is complete. Provide the result inside the brackets:  
  - For text-based answers, write the answer directly.  
  - If the task is impossible to complete, use "N/A" as the answer.  

## RULES

1. Only issue actions that are valid based on the current observation.  
2. Perform one action at a time.  
3. Follow the reasoning examples and proceed step by step before issuing the next action.  
4. Format actions correctly. Use the following structure:  
   - Start with: *"In summary, the next action I will perform is"*  
   - Followed by the action in backticks, e.g., click [1234].  
5. Use the stop action once you achieve the objective. Do not generate any further output after issuing the stop action.  

By adhering to these instructions and leveraging the available actions effectively, you will successfully complete the assigned web-based tasks.
'''

prompt_input_template = '''
# OBSERVATION

{full_axtree}

# URL

{url}

# OBJECTIVE

{objective}

# PREVIOUS ACTIONS

{action_list}
'''

prompt_output_template = '''
First, Let's find the most relevant part of axtree that I need:

{retrieved_axtree}

Therefore, the next action I will perform is:

```json
{action}
```
'''

action_template = '''
## Action {i}
- action_type: {action_type}
- action_value: {action_value}
'''

def get_prompt_input(formatted_axtree, href, objective, step_num, steps):
    """
    根据格式化的 axtree、当前链接、目标以及历史步骤，生成 prompt 输入。
    """
    action_list = ""
    for previous_step_num, previous_step in enumerate(steps):
        if previous_step_num < step_num:
            tmp_action = action_template.format(
                i=previous_step_num,
                action_type=previous_step["type"],
                action_value=previous_step["value"]
            )
            action_list += tmp_action
        else:
            break

    return prompt_input_template.format(
        full_axtree=formatted_axtree.strip(), 
        url=href, 
        objective=objective, 
        action_list=action_list
    )

def setup_logging(user_name, log_dir="logs"):
    """Set up logging configuration"""
    log_dir = f"./logs/{log_dir}"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"{user_name}_{timestamp}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

def main(user_name, log_dir, start_idx, end_idx, prefix):
    # Set up logging
    setup_logging(user_name, log_dir)
    logging.info(f"Starting to process data for user: {user_name}")

    # 第一步：导入用户标注数据，下载对应的 axtree，同时格式化并根据每个 step 中的 path 去 retrieve 出 node

    # 用户标注数据目录和文件列表
    user_annotate_dir = f"./query_results3/{prefix}"
    all_user_annotate_files = os.listdir(user_annotate_dir)
    # print(all_user_annotate_files)

    # 建立存储 axtree 的文件夹 raw_axtree, formatted_axtree, retrieved_axtree
    raw_axtree_dir = f"./raw_axtree/{prefix}"
    formatted_axtree_dir = f"./formatted_axtree/{prefix}"
    retrieved_axtree_dir = f"./retrieved_axtree/{prefix}"

    for directory in [raw_axtree_dir, formatted_axtree_dir, retrieved_axtree_dir]:
        if not os.path.exists(directory):
            os.makedirs(directory)

    # 读取指定用户的文件并切片
    user_annotate_file = os.path.join(user_annotate_dir, prefix + "_" + user_name + ".json")
    # 如果end_idx为-1，则取全部数据
    if end_idx == -1:
        end_idx = len(json.load(open(user_annotate_file, "r")))
    with open(user_annotate_file, "r") as f:
        user_annotate_data = json.load(f)[start_idx:end_idx]

    # 遍历 user_annotate_data，对每个任务标注生成 axtree，并存储结果
    axtid_cnt = 0
    total_cnt = 0
    not_found_cnt = 0
    new_user_annotate_data = []

    for task_num, task in enumerate(user_annotate_data):
        logging.info(f"Processing task {task_num} of {len(user_annotate_data)}")
        new_task = copy.deepcopy(task)
        steps_ls = json.loads(task["steps"])
        new_steps_ls = []

        for step_num, step in enumerate(steps_ls):
            new_step = copy.deepcopy(step)
            if "axTree" in step and step["axTree"] is not None:
                axTree_url = step["axTree"]
                restore_raw_dir = os.path.join(raw_axtree_dir, user_name, str(task_num))
                restore_raw_path = os.path.join(restore_raw_dir, f"{step_num}.json")
                if not os.path.exists(restore_raw_dir):
                    os.makedirs(restore_raw_dir)

                # 下载 axTree 并存储到指定位置
                download_json(axTree_url, restore_raw_path)

                # 格式化 raw axtree 并生成 formatted_axtree
                restore_formatted_dir = os.path.join(formatted_axtree_dir, user_name, str(task_num))
                restore_formatted_path = os.path.join(restore_formatted_dir, f"{step_num}.txt")
                if not os.path.exists(restore_formatted_dir):
                    os.makedirs(restore_formatted_dir)

                with open(restore_raw_path, "r") as f:
                    raw_axtree = json.load(f)
                if raw_axtree is None:
                    logging.warning(f"Raw axtree is None, {user_name}, {task_num}, {step_num}")
                    raw_axtree = {}
                formatted_nodes = format_node(raw_axtree)
                formatted_axtree = "".join(node + '\n' for node in formatted_nodes)

                with open(restore_formatted_path, "w") as f:
                    f.write(formatted_axtree)

                # 根据 path 找到 axtree 中的节点，并生成 retrieved_axtree
                path = ["html"] + step["path"].split('>')
                retrieved_axtree = ""
                raw_retrieved_axtree = find_node_by_path(raw_axtree, path)
                if raw_retrieved_axtree is None:
                    logging.warning(f"No node found in path {path}, {user_name}, {task_num}, {step_num}")
                    not_found_cnt += 1
                    raw_retrieved_axtree = {}

                # 更新 new_step 中的 axtId 信息
                axtid = raw_retrieved_axtree.get("attributes", {}).get("data-imean-axt-id", "")
                if "axtId" in new_step:
                    if axtid != new_step["axtId"]:
                        logging.warning(f"ID mismatch: existing={new_step['axtId']}, found={axtid}")
                    assert axtid == new_step["axtId"]
                new_step["axtId"] = axtid
                if axtid:
                    axtid_cnt += 1
                total_cnt += 1

                # 格式化 retrieved axtree 并保存
                for node in format_node(raw_retrieved_axtree):
                    retrieved_axtree += node + '\n'
                restore_retrieved_dir = os.path.join(retrieved_axtree_dir, user_name, str(task_num))
                restore_retrieved_path = os.path.join(restore_retrieved_dir, f"{step_num}.txt")
                if not os.path.exists(restore_retrieved_dir):
                    os.makedirs(restore_retrieved_dir)
                with open(restore_retrieved_path, "w") as f:
                    f.write(retrieved_axtree)
            new_steps_ls.append(new_step)
        new_task["steps"] = json.dumps(new_steps_ls)
        new_user_annotate_data.append(new_task)

    # 修改输出文件名，加入范围信息
    new_user_annotate_file = os.path.join(
        user_annotate_dir, 
        f"{user_name}_{args.prefix}_{start_idx}_{end_idx}_new.json"
    )
    print(new_user_annotate_file)
    with open(new_user_annotate_file, "w") as f:
        json.dump(new_user_annotate_data, f, ensure_ascii=False, indent=2)

    # 第二步：组 sft 数据，按 user 存储

    # 修改 sft 数据文件名
    sft_data_file = os.path.join(
        f"./sft_data/{prefix}", 
        f"{user_name}_{prefix}_{start_idx}_{end_idx}_sft.jsonl"
    )
    os.makedirs(os.path.dirname(sft_data_file), exist_ok=True)
    
    with open(sft_data_file, 'w', encoding='utf-8') as output_file:
        for task_num, task in enumerate(new_user_annotate_data):
            steps = json.loads(task["steps"])
            objective = task['title']
            for step_num, step in enumerate(steps):
                if "axTree" in step and step["axTree"]:
                    formatted_axtree_path = os.path.join(f"./formatted_axtree/{prefix}", user_name, str(task_num), f"{step_num}.txt")
                    retrieved_axtree_path = os.path.join(f"./retrieved_axtree/{prefix}", user_name, str(task_num), f"{step_num}.txt")

                    try:
                        # 读取格式化后的 axtree 和 retrieved axtree 数据
                        with open(formatted_axtree_path, 'r', encoding='utf-8') as f:
                            formatted_axtree = f.read()
                        with open(retrieved_axtree_path, 'r', encoding='utf-8') as f:
                            retrieved_axtree = f.read()

                        # 如果 retrieved_axtree 或 formatted_axtree 为空，则跳过
                        if not retrieved_axtree.strip() or not formatted_axtree.strip():
                            continue

                        prompt_input = get_prompt_input(
                            formatted_axtree,
                            step["href"],
                            objective,
                            step_num,
                            copy.deepcopy(steps)
                        )

                        action = {
                            "action_type": step["type"],
                            "action_id": step["axtId"],
                            "action_value": step["value"]
                        }
                        action_json = json.dumps(action, ensure_ascii=False, indent=2)
                        prompt_output = prompt_output_template.format(
                            retrieved_axtree=retrieved_axtree.strip(),
                            action=action_json
                        )

                        data_dict = {
                            "prompt_system": prompt_system,
                            "prompt_input": prompt_input,
                            "prompt_output": prompt_output,
                            "url": step["href"],
                            "user_name": user_name,
                            "task_num": task_num,
                            "step_num": step_num
                        }

                        # 写入单行 JSON
                        output_file.write(json.dumps(data_dict, ensure_ascii=False) + '\n')
                        
                    except Exception as e:
                        logging.error(f"Error processing task {task_num}, step {step_num}: {str(e)}")
                        continue

    logging.info(f"SFT data saved to {sft_data_file}")
    logging.info(f"Statistics - axtid_cnt: {axtid_cnt}, node_not_found_cnt: {not_found_cnt}, total_cnt: {total_cnt}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process user annotate data")
    parser.add_argument("--user_name", type=str, required=True, help="User name for processing data")
    parser.add_argument("--log_dir", type=str, default="logs", help="Directory name for storing logs under ./logs/")
    parser.add_argument("--start_idx", type=int, default=0, help="Start index of data to process")
    parser.add_argument("--end_idx", type=int, default=-1, help="End index of data to process")
    parser.add_argument("--prefix", type=str, default="selected_50", help="Prefix used to specify the data directory to process")
    args = parser.parse_args()
    
    main(args.user_name, args.log_dir, args.start_idx, args.end_idx, args.prefix)
