import os
import json
import random

def select_random_samples(input_directory, prefix, seed=42):
    # 设置随机数种子以确保结果可复现
    random.seed(seed)
    
    # 遍历目录中的所有json文件
    for filename in os.listdir(input_directory):
        if filename.endswith('.json'):
            file_path = os.path.join(input_directory, filename)
            
            # 读取json文件
            with open(file_path, 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                    
                    # 如果数据量大于50，随机抽取50条
                    if len(data) > 50:
                        selected_data = random.sample(data, 50)
                    else:
                        selected_data = data
                    
                    # 构造新文件名和路径
                    new_filename = f"{prefix}_{filename}"
                    output_path = os.path.join(input_directory, prefix, new_filename)
                    
                    # 保存抽样后的数据
                    with open(output_path, 'w', encoding='utf-8') as outf:
                        json.dump(selected_data, outf, ensure_ascii=False, indent=2)
                    
                    print(f"Processed {filename}: Selected {len(selected_data)} samples")
                    
                except json.JSONDecodeError as e:
                    print(f"Error reading {file_path}: {e}")

# 使用示例
input_directory = "query_results3"
prefix = "selected_50"
seed = 42
select_random_samples(input_directory, prefix, seed)