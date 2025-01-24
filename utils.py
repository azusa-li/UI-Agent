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
            
        # print(f"Successfully downloaded JSON to {output_file}")
        
    except requests.exceptions.RequestException as e:
        print(f"Error downloading the file: {e}")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")


def find_node_by_path(node, path, current_level=0):
    """
    递归遍历 axtree，寻找路径为 path 的节点。
    
    :param node: 当前节点
    :param path: 路径数组（如 ["body", "div", "p"]）
    :param current_level: 当前路径匹配到的层级
    :return: 如果找到匹配的节点，返回节点对象；否则返回 None
    """
    
    if node is None:
        return None
    
    # 获取当前节点的标签
    html_tag = node.get("attributes", {}).get("html_tag", "")

    # 检查当前节点是否匹配路径的当前部分
    if html_tag != path[current_level]:
        return None

    # 如果已经匹配到路径的最后一级，返回当前节点
    if current_level == len(path) - 1:
        return node

    # 遍历子节点，递归查找下一层级
    for child in node.get("children", []):
        result = find_node_by_path(child, path, current_level + 1)
        if result:
            return result

    # 如果没有找到，返回 None
    return None

def format_node(node, level=0):
    result = []
    indent = "  " * level  # 2 spaces per level
    
    if node is None:
        return result
    
    # Get attributes for current node
    axt_id = node.get("attributes", {}).get("data-imean-axt-id")
    role = node.get("role")
    name = node.get("name")
    
    # Add formatted string if node has all required attributes
    if axt_id and role:
        formatted = indent + f"[{axt_id}] {role}"
        if name:
            formatted += f" '{name}'"
        result.append(formatted)
    
    # Recursively process children
    children = node.get("children", [])
    for child in children:
        result.extend(format_node(child, level + 1))
        
    return result