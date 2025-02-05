import argparse
import json
import os
import copy
import pandas as pd
from utils import *
import logging
import datetime

from prompt import *

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

def main(user_name, log_dir, start_idx, end_idx, prefix, force_download):
    # Set up logging
    setup_logging(user_name, log_dir)
    logging.info(f"Starting to process data for user: {user_name}")

    # 第一步：导入用户标注数据，下载对应的 axtree，同时格式化并根据每个 step 中的 path 去 retrieve 出 node

    # 用户标注数据目录和文件列表
    user_annotate_dir = f"./data/query_results3/{prefix}"
    all_user_annotate_files = os.listdir(user_annotate_dir)
    # print(all_user_annotate_files)

    # 建立存储 axtree 的文件夹 raw_axtree, formatted_axtree, cleaned_axtree, retrieved_axtree
    raw_axtree_dir = f"./data/raw_axtree/{prefix}"
    formatted_axtree_dir = f"./data/formatted_axtree/{prefix}"
    cleaned_axtree_dir = f"./data/cleaned_axtree/{prefix}"
    retrieved_axtree_dir = f"./data/retrieved_axtree/{prefix}"

    for directory in [raw_axtree_dir, formatted_axtree_dir, cleaned_axtree_dir, retrieved_axtree_dir]:
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
    already_existing_axtid_cnt = 0
    new_user_annotate_data = []

    for task_num, task in enumerate(user_annotate_data):
        logging.info(f"Processing task {task_num} of {len(user_annotate_data)}")
        new_task = copy.deepcopy(task)
        steps_ls = json.loads(task["steps"])
        new_steps_ls = []

        for step_num, step in enumerate(steps_ls):
            new_step = copy.deepcopy(step)
            if "axTree" in step and step["axTree"]:
                logging.info(f"Processing step {step_num}")
                axTree_url = step["axTree"]
                restore_raw_dir = os.path.join(raw_axtree_dir, user_name, str(task_num))
                restore_raw_path = os.path.join(restore_raw_dir, f"{step_num}.json")
                if not os.path.exists(restore_raw_dir):
                    os.makedirs(restore_raw_dir)

                # 下载 axTree 并存储到指定位置
                # 如果 raw axtree已经存在，并且 force_download 为 False，则跳过下载
                if not os.path.exists(restore_raw_path) or force_download:
                    download_json(axTree_url, restore_raw_path)
                    logging.info(f"Downloaded axTree to {restore_raw_path}")
                else:
                    logging.info(f"Using existing axTree from {restore_raw_path}")
                    
                # 读取 raw axtree
                with open(restore_raw_path, "r") as f:
                    raw_axtree = json.load(f)
                if raw_axtree is None:
                    logging.warning(f"Raw axtree is None, {user_name}, {task_num}, {step_num}")
                    raw_axtree = {}
                    
                # 清洗 axTree 得到 cleaned_axtree
                restore_cleaned_dir = os.path.join(cleaned_axtree_dir, user_name, str(task_num))
                restore_cleaned_path = os.path.join(restore_cleaned_dir, f"{step_num}.json")
                if not os.path.exists(restore_cleaned_dir):
                    os.makedirs(restore_cleaned_dir)
                cleaned_axtree = clean_axtree(raw_axtree)
                with open(restore_cleaned_path, "w") as f:
                    json.dump(cleaned_axtree, f, ensure_ascii=False, indent=2)

                # 格式化 cleaned axtree 并生成 formatted_axtree
                restore_formatted_dir = os.path.join(formatted_axtree_dir, user_name, str(task_num))
                restore_formatted_path = os.path.join(restore_formatted_dir, f"{step_num}.txt")
                if not os.path.exists(restore_formatted_dir):
                    os.makedirs(restore_formatted_dir)
                formatted_axtree = format_node(cleaned_axtree)
                with open(restore_formatted_path, "w", encoding="utf-8") as f:
                    f.write(formatted_axtree)

                # 尝试通过 axtid 和 path 两种方式在 cleaned_axtree 中查找节点 得到 raw_retrieved_axtree
                axtid = step.get("axtId", "")
                path = ["html"] + step["path"].split('>')
                retrieved_axtree = ""
                raw_retrieved_axtree = None
                
                # 优先使用 axtid 查找
                if axtid:
                    raw_retrieved_axtree = find_node_by_axtid(cleaned_axtree, axtid)
                
                # 如果 axtid 查找失败，尝试使用 path 查找
                if raw_retrieved_axtree is None:
                    logging.warning(f"No node found in axtid {axtid}, {user_name}, {task_num}, {step_num}")
                    raw_retrieved_axtree = find_node_by_path(cleaned_axtree, path)
                    if raw_retrieved_axtree is None:
                        logging.warning(f"No node found in path {path}, {user_name}, {task_num}, {step_num}")
                        logging.warning(f"Node not found using either method, {user_name}, {task_num}, {step_num}")
                        raw_retrieved_axtree = {}
                
                if not raw_retrieved_axtree:
                    not_found_cnt += 1

                # 更新 new_step 中的 axtId 信息
                axtid = raw_retrieved_axtree.get("attributes", {}).get("data-imean-axt-id", "")
                if "axtId" in new_step:
                    already_existing_axtid_cnt += 1
                    if axtid != new_step["axtId"]:
                        logging.warning(f"ID mismatch: existing={new_step['axtId']}, found={axtid}")
                    assert axtid == new_step["axtId"]
                new_step["axtId"] = axtid
                if axtid:
                    axtid_cnt += 1
                total_cnt += 1
                
                # 过滤掉step-value和raw_retrieved_axtree-name不一致并相似度小于0.8的step 标记为invalid
                # ！！注意：这里不要改变原有steps的数量，仅修改原有steps里每个step的相应属性，并标记出组成sft data时是否需要过滤掉
                new_step_value = new_step.get("value", "")
                if new_step_value == "":
                    new_step["is_valid"] = False
                else:
                    current_node_name = raw_retrieved_axtree.get("name", "")
                    current_node_filtered = raw_retrieved_axtree.get("is_filtered", False)
                    if current_node_name == "":
                        new_step["is_valid"] = False
                    elif current_node_filtered:
                        new_step["is_valid"] = False
                    elif new_step_value.strip().lower() == current_node_name.strip().lower() or calculate_similarity(new_step_value, current_node_name) > 0.8:
                        new_step["is_valid"] = True
                    else:
                        logging.warning(f"Step value and retrieved axtree name mismatch: step={new_step_value}, retrieved_axtree={current_node_name}, {user_name}, {task_num}, {step_num}")
                        new_step["is_valid"] = False

                # 格式化 retrieved axtree 并保存
                retrieved_axtree = format_node(raw_retrieved_axtree)
                restore_retrieved_dir = os.path.join(retrieved_axtree_dir, user_name, str(task_num))
                restore_retrieved_path = os.path.join(restore_retrieved_dir, f"{step_num}.txt")
                if not os.path.exists(restore_retrieved_dir):
                    os.makedirs(restore_retrieved_dir)
                with open(restore_retrieved_path, "w", encoding="utf-8") as f:
                    f.write(retrieved_axtree)
            new_steps_ls.append(new_step)
        new_task["steps"] = json.dumps(new_steps_ls, ensure_ascii=False)
        new_user_annotate_data.append(new_task)

    # 修改输出文件名，加入范围信息
    new_user_annotate_file = os.path.join(
        user_annotate_dir, 
        f"{user_name}_{args.prefix}_{start_idx}_{end_idx}_new.json"
    )
    logging.info(new_user_annotate_file)
    with open(new_user_annotate_file, "w") as f:
        json.dump(new_user_annotate_data, f, ensure_ascii=False, indent=2)

    # 第二步：组 sft 数据，按 user 存储
    logging.info(f"Synthesizing sft data for {user_name}, {prefix}, {start_idx}, {end_idx}")
    
    # 修改 sft 数据文件名
    sft_data_file = os.path.join(
        f"./data/sft_data/{prefix}", 
        f"{user_name}_{prefix}_{start_idx}_{end_idx}_sft.jsonl"
    )
    os.makedirs(os.path.dirname(sft_data_file), exist_ok=True)
    
    with open(sft_data_file, 'w', encoding='utf-8') as output_file:
        for task_num, task in enumerate(new_user_annotate_data):
            steps = json.loads(task["steps"])
            objective = task['title'].replace("-", "").strip()
            for step_num, step in enumerate(steps):
                if "axTree" in step and step["axTree"] and step["is_valid"]:
                    formatted_axtree_path = os.path.join(formatted_axtree_dir, user_name, str(task_num), f"{step_num}.txt")
                    retrieved_axtree_path = os.path.join(retrieved_axtree_dir, user_name, str(task_num), f"{step_num}.txt")

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
    logging.info(f"Statistics - axtid_cnt: {axtid_cnt}, already_existing_axtid_cnt: {already_existing_axtid_cnt}, node_not_found_cnt: {not_found_cnt}, total_cnt: {total_cnt}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process user annotate data")
    parser.add_argument("--user_name", type=str, required=True, help="User name for processing data")
    parser.add_argument("--log_dir", type=str, default="logs", help="Directory name for storing logs under ./logs/")
    parser.add_argument("--start_idx", type=int, default=0, help="Start index of data to process")
    parser.add_argument("--end_idx", type=int, default=-1, help="End index of data to process")
    parser.add_argument("--prefix", type=str, default="selected_50", help="Prefix used to specify the data directory to process")
    parser.add_argument("--force_download", action="store_true", help="Force download raw axTree even if it already exists")
    args = parser.parse_args()
    
    main(args.user_name, args.log_dir, args.start_idx, args.end_idx, args.prefix, args.force_download)
