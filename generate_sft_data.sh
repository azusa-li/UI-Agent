#!/bin/bash

# Define users array - one user per line for better readability
users=(
    "Cyberpunk"
    "HATBTBS"
    "Im"
    "Jingqiu"
    "Kyle"
    "Siing"
    "YH"
    "aliuliuliuliu"
    "balidexiaocaifeng"
    "cceatmore"
)
    # "daidaiyoudianer"
    # "dcynsd"
    # "haoyunlai"
    # "lanlantoudinghuahua"
    # "miaolegemi"
    # "pingdanershiyu"
    # "qingchen"
    # "qingfengmingyueMoonWind"
    # "qingfengmingyueyibuzai"
    # "qisanljyyy"
    # "sk"
    # "yashiming"
    # "ye"


# logs下的子目录
log_dir="20250124_1225"
prefix="selected_50"
# 处理每个用户
for user in "${users[@]}"; do
    echo "Processing user: $user"
    python synthesize_sft_data.py --user_name "$user" --log_dir "$log_dir" --prefix "$prefix"
    echo "Completed processing for $user"
    echo "----------------------------------------"
done

echo "All users processed successfully!"