#!/bin/bash

today=$(date +%F)
year=$(date +%Y)
# 定义基础输出目录
BASE_DIR="/root/.flow/account/data/${year}"

# 确保目录存在
mkdir -p "$BASE_DIR"

# 定义需要处理的账单文件数组
INPUT_FILES=(
    "/root/.flow/data/alipay/${today}.csv"
    "/root/.flow/data/wechat/${today}.xlsx"
)

# 遍历每一个文件进行处理
for input_file in "${INPUT_FILES[@]}"; do
    
    # 1. 检查文件到底存不存在
    if [ ! -f "$input_file" ]; then
        echo "跳过: 未找到文件 $input_file"
        continue
    fi

    # === 新增防重复核心逻辑：MD5 校验 ===
    # 为每个文件生成一个记录指纹的隐藏文件 (例如 .csv.md5)
    marker_file="${input_file}.md5"
    current_md5=$(md5sum "$input_file" | awk '{print $1}')
    
    if [ -f "$marker_file" ]; then
        last_md5=$(cat "$marker_file")
        if [ "$current_md5" == "$last_md5" ]; then
            echo "拦截: 文件未发生变化，跳过处理以防重复写入 -> $input_file"
            continue
        fi
    fi
    # ==========================================

    echo "正在处理账单: $input_file"

    # 动态生成 provider 参数
    PROVIDER_ARG=""
    if [[ "$input_file" == *"wechat"* ]]; then
        PROVIDER_ARG="-p wechat"
    fi

    # 把 $PROVIDER_ARG 加到命令里（如果是支付宝，它就是空的，不影响）
    /root/.local/bin/bflow -c /root/.flow/bill.yaml trans $PROVIDER_ARG -s "$input_file" \
    | sed 's/\x1b\[[0-9;]*m//g' \
    | jq -r 'to_entries[] | .key as $k | .value[] | "\($k)\t\(.|@base64)"' \
    | while IFS=$'\t' read -r filename content; do
        
        # 写入目标文件路径判断
        if [[ "$filename" =~ ^[0-9]+$ ]]; then
            target_file="${BASE_DIR}/${year}-${filename}.bean"
        else
            target_file="${BASE_DIR}/${filename}.bean"
        fi

        # 写入文件
        echo "$content" | base64 -d >> "$target_file"
        echo "" >> "$target_file" 
    done

    # === 处理成功后，记录该文件的最新指纹 ===
    echo "$current_md5" > "$marker_file"
    echo "处理完成: $input_file"
    # ==========================================
done