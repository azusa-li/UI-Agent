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

def find_node_by_axtid(node, axtid, current_level=0):
    """
    递归遍历 axtree，寻找指定 axtid 的节点。
    
    :param node: 当前节点
    :param axtid: 要查找的节点ID（字符串）
    :param current_level: 当前遍历的层级（用于调试）
    :return: 如果找到匹配的节点，返回节点对象；否则返回 None
    """
    if node is None:
        return None
    
    # 获取当前节点的 axtid
    node_axtid = node.get("attributes", {}).get("data-imean-axt-id")
    
    # 检查当前节点是否匹配
    if node_axtid == axtid:
        return node
    
    # 遍历子节点，递归查找
    for child in node.get("children", []):
        result = find_node_by_axtid(child, axtid, current_level + 1)
        if result:
            return result
    
    # 如果没有找到，返回 None
    return None

def find_nearest_text(node, visited_nodes=None, max_depth=2):
    """
    查找节点最近的有意义的文本内容
    """
    if visited_nodes is None:
        visited_nodes = set()
    
    # 防止重复访问和超出深度限制
    node_id = node.get("attributes", {}).get("data-imean-axt-id")
    if not node_id or node_id in visited_nodes or max_depth < 0:
        return "", float('inf')
    
    visited_nodes.add(node_id)
    
    # 检查当前节点的文本
    if node.get("name", "").strip():
        return node["name"], 0
    
    min_depth = float('inf')
    best_content = ""
    
    # 检查子节点
    children = node.get("children", [])
    for child in children:
        if child:
            content, depth = find_nearest_text(child, visited_nodes, max_depth - 1)
            if content.strip() and depth < min_depth:
                min_depth = depth
                best_content = content
    
    # 检查兄弟节点（通过共同的父节点的其他子节点）
    if node.get("children"):
        for sibling in node.get("children", []):
            if sibling and sibling != node:
                content, depth = find_nearest_text(sibling, visited_nodes, max_depth - 1)
                if content.strip() and depth < min_depth:
                    min_depth = depth
                    best_content = content
    
    return (best_content, min_depth + 1) if best_content else ("", float('inf'))

def clean_axtree(node):
    """
    清洗axtree节点，过滤掉无意义的节点，同时考虑附近的文本内容
    
    :param node: axtree节点
    :return: 清洗后的节点（带有is_filtered标志）
    """
    if node is None:
        return None
    
    # 获取基本属性
    role = node.get("role")
    name = node.get("name")
    node_id = node.get("attributes", {}).get("data-imean-axt-id", "unknown")
    
    # print(f"处理节点: ID={node_id}, role={role}, name={name}")
    # print(f"节点 {node_id} 的直接子节点 IDs: {[child.get('attributes', {}).get('data-imean-axt-id', 'unknown') for child in node.get('children', [])]}")
    
    # 首先处理所有子节点
    cleaned_children = []
    for child in node.get("children", []):
        cleaned_child = clean_axtree(child)
        if cleaned_child:
            cleaned_children.append(cleaned_child)
    
    # 创建节点副本
    cleaned_node = node.copy()
    cleaned_node["children"] = cleaned_children
    if name:
        cleaned_node["name"] = name
    
    # 判断节点是否应该被过滤
    meaningful_roles = {
        'document', 'button', 'link', 'heading', 'list', 'listitem',
        'textbox', 'img', 'paragraph', 'form', 'contentinfo', 'banner',
        'navigation', 'region', 'iframe'
    }
    
    # 如果节点没有name，尝试查找最近的文本
    if not name and role in meaningful_roles:
        name, distance = find_nearest_text(node)
        if distance > 2:
            name = ""
    
    should_include = (
        (name and name.strip()) or
        (role in meaningful_roles and role != 'img') or  # 排除img的一般性判断
        (role == 'img' and name and name.strip()) or    # img需要有name才包含
        (role == 'generic' and (name or any(child.get("role") in meaningful_roles 
                                          for child in node.get("children", []))))
    )
    
    # 添加过滤标志
    cleaned_node["is_filtered"] = not should_include
    # if not should_include:
    #     print(f"节点被过滤: ID={node_id}, role={role}, name={name}")
    
    return cleaned_node


def format_node(node, level=0):
    """
    格式化单个节点，将其转换为字符串表示
    
    :param node: 已清洗的axtree节点
    :param level: 缩进级别
    :return: 格式化后的字符串
    """
    if node is None:
        return ""
    
    result = []
    indent = "  " * level
    
    # 如果节点没有被过滤，添加当前节点的格式化结果
    if not node.get("is_filtered", False):
        axt_id = node.get("attributes", {}).get("data-imean-axt-id")
        role = node.get("role")
        name = node.get("name")
        
        if axt_id and role:
            formatted = indent + f"[{axt_id}] {role}"
            if name:
                formatted += f" '{name}'"
            result.append(formatted)
    
    # 无论节点是否被过滤，都处理其子节点
    for child in node.get("children", []):
        child_result = format_node(child, level + (0 if node.get("is_filtered", False) else 1))
        if child_result:
            result.extend(child_result.split('\n'))
    
    return '\n'.join(result)

def calculate_similarity(str1, str2):
    """计算两个字符串的相似度，基于编辑距离"""
    from Levenshtein import distance
    max_len = max(len(str1), len(str2))
    if max_len == 0:
        return 1.0
    return 1 - distance(str1, str2) / max_len