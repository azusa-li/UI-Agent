import os
import json
from collections import defaultdict

def merge_json_files(input_directory, output_directory):
    # 用于存储按前缀分组的文件路径
    prefix_files = defaultdict(list)
    
    # 遍历目录中的所有json文件
    for filename in os.listdir(input_directory):
        if filename.endswith('.json'):
            # 获取前缀（第一个下划线之前的部分）
            prefix = filename.split('_')[0]
            prefix_files[prefix].append(os.path.join(input_directory, filename))
    
    # 处理每个前缀的文件组
    for prefix, file_paths in prefix_files.items():
        merged_data = []
        
        # 读取并合并每个文件的内容
        for file_path in file_paths:
            with open(file_path, 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                    if isinstance(data, list):
                        merged_data.extend(data)
                    else:
                        merged_data.append(data)
                except json.JSONDecodeError as e:
                    print(f"Error reading {file_path}: {e}")
        
        # 保存合并后的文件
        output_path = os.path.join(output_directory, f"{prefix}.json")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(merged_data, f, ensure_ascii=False, indent=2)
        
        print(f"Merged {len(file_paths)} files into {output_path}")

# 使用示例
input_directory = "query_results3/raw_user_data"
output_directory = "query_results3/"
merge_json_files(input_directory, output_directory)


'''
Merged 17 files into query_results3/dcynsd.json
Merged 35 files into query_results3/Kyle.json
Merged 57 files into query_results3/qisanljyyy.json
Merged 45 files into query_results3/haoyunlai.json
Merged 21 files into query_results3/sk.json
Merged 18 files into query_results3/cceatmore.json
Merged 16 files into query_results3/Siing.json
Merged 9 files into query_results3/YH.json
Merged 33 files into query_results3/Im.json
Merged 16 files into query_results3/aliuliuliuliu.json
Merged 18 files into query_results3/daidaiyoudianer.json
Merged 14 files into query_results3/ye.json
Merged 19 files into query_results3/yashiming.json
Merged 38 files into query_results3/HATBTBS.json
Merged 6 files into query_results3/lanlantoudinghuahua.json
Merged 21 files into query_results3/qingfengmingyueyibuzai.json
Merged 13 files into query_results3/qingchen.json
Merged 5 files into query_results3/balidexiaocaifeng.json
Merged 6 files into query_results3/miaolegemi.json
Merged 4 files into query_results3/pingdanershiyu.json
Merged 5 files into query_results3/Cyberpunk.json
Merged 4 files into query_results3/Jingqiu.json
Merged 2 files into query_results3/qingfengmingyueMoonWind.json
'''
