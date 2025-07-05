import re
import csv
import sys

def extract_markdown_titles(file_path):
    # 存储标题的列表
    titles = []
    
    # 一级标题计数器
    current_h1 = ""
    current_h2 = ""
    
    # 读取Markdown文件
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            # 匹配一级标题
            h1_match = re.match(r'^# (.+)$', line.strip())
            if h1_match:
                current_h1 = h1_match.group(1).strip()
                titles.append([current_h1, "", ""])
                continue
            
            # 匹配二级标题
            h2_match = re.match(r'^## (.+)$', line.strip())
            if h2_match:
                current_h2 = h2_match.group(1).strip()
                titles.append(["", current_h2, ""])
                continue
            
            # 匹配三级标题
            h3_match = re.match(r'^### (.+)$', line.strip())
            if h3_match:
                h3_title = h3_match.group(1).strip()
                titles.append(["", "", h3_title])
                continue
    
    return titles

def export_to_csv(titles, output_file):
    # 导出到CSV文件
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        csvwriter = csv.writer(csvfile)
        # 写入标题行
        csvwriter.writerow(['一级标题', '二级标题', '三级标题'])
        # 写入数据
        csvwriter.writerows(titles)

def main():
    # 检查命令行参数
    if len(sys.argv) < 3:
        print("使用方法: python script.py <输入的Markdown文件路径> <输出的CSV文件路径>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    # 提取标题
    titles = extract_markdown_titles(input_file)
    
    # 导出到CSV
    export_to_csv(titles, output_file)
    
    print(f"标题已成功导出到 {output_file}")

if __name__ == "__main__":
    main()