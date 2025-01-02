import requests
import json

def download_json(url, output_file='output.json'):
    try:
        # 发送GET请求获取数据
        response = requests.get(url)
        response.raise_for_status()  # 检查请求是否成功
        
        # 将JSON数据保存到文件
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(response.json(), f, ensure_ascii=False, indent=2)
            
        print(f"Successfully downloaded JSON to {output_file}")
        
    except requests.exceptions.RequestException as e:
        print(f"Error downloading the file: {e}")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")

# 使用示例
url = "https://data.imean.tech/temp-uploads/1733126914216-lrAs4.json"
download_json(url, 'downloaded_data.json')