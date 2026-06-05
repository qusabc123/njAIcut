"""
封面生成器
从开头素材第一帧截图 + 用PIL叠加项目名称文字 + 直接写入剪映草稿封面

用法: python generate_cover.py <项目路径> <草稿名> [--index N]
"""
import sys, os, subprocess, json, shutil
from PIL import Image, ImageDraw, ImageFont


def generate_cover(project_dir, draft_name, group_index=1):
    """生成封面并写入草稿"""
    
    # ===== 1. 找到开头素材 =====
    开头_dir = os.path.join(project_dir, '开头')
    assert os.path.isdir(开头_dir), f"错误: 缺少 {开头_dir}"
    
    开头列表 = sorted([f for f in os.listdir(开头_dir) if f.lower().endswith('.mov')])
    assert len(开头列表) >= group_index
    开_文件 = 开头列表[group_index - 1]
    开_路径 = os.path.join(开头_dir, 开_文件)
    print(f'[封面] 开头素材: {开_文件}')
    
    # ===== 2. 项目名称 =====
    项目名 = os.path.basename(os.path.normpath(project_dir))
    print(f'[封面] 项目名称: {项目名}')
    
    # ===== 3. 截取开头第一帧作为底图 =====
    底图路径 = os.path.join(project_dir, '_cover_bg.jpg')
    subprocess.run([
        'ffmpeg', '-y', '-i', 开_路径,
        '-vframes', '1',
        '-q:v', '2',
        '-vf', 'scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920',
        底图路径
    ], capture_output=True, check=True)
    print(f'[封面] 底图已生成')
    
    # ===== 4. 用PIL叠加文字 =====
    img = Image.open(底图路径).convert('RGB')
    draw = ImageDraw.Draw(img)
    
    # 找系统俊雅体 / 回退到中文字体
    字体路径 = None
    for p in [
        '/System/Library/Fonts/PingFang.ttc',
        '/System/Library/Fonts/STHeiti Light.ttc',
        '/Library/Fonts/Arial.ttf',
    ]:
        if os.path.exists(p):
            字体路径 = p
            break
    
    if 字体路径:
        # 根据文字长度动态调整字号（封面中间大标题）
        font_size = min(180, 3600 // len(项目名))
        try:
            font = ImageFont.truetype(字体路径, font_size)
        except:
            font = ImageFont.load_default()
    else:
        font = ImageFont.load_default()
    
    # 文字颜色 #fdfcb2
    文字颜色 = (253, 252, 178)
    
    # 阴影颜色 #000000 60%
    阴影颜色 = (0, 0, 0)
    
    # 获取文字尺寸，居中绘制
    bbox = draw.textbbox((0, 0), 项目名, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (1080 - text_w) // 2
    y = (1920 - text_h) // 2
    
    # 先画阴影（偏移）
    阴影偏移 = 6
    draw.text((x + 阴影偏移, y + 阴影偏移), 项目名, fill=阴影颜色 + (153,), font=font)  # 153=60%*255
    # 再画主文字
    draw.text((x, y), 项目名, fill=文字颜色, font=font)
    
    # ===== 5. 保存封面图 =====
    封面输出 = os.path.join(project_dir, '_cover_output.jpg')
    img.save(封面输出, 'JPEG', quality=92)
    print(f'[封面] 文字: 俊雅体(回退) | #fdfcb2 | 居中 | 阴影#000000 60%')
    print(f'[封面] 封面已生成')
    
    # ===== 6. 写入到剪映草稿 =====
    draft_dir = '/Users/nj/Movies/JianyingPro/User Data/Projects/com.lveditor.draft'
    草稿路径 = os.path.join(draft_dir, draft_name)
    
    if os.path.isdir(草稿路径):
        # 复制封面到底图
        shutil.copy2(封面输出, os.path.join(草稿路径, 'draft_cover.jpg'))
        
        # 更新 draft_meta_info.json
        meta_path = os.path.join(草稿路径, 'draft_meta_info.json')
        if os.path.exists(meta_path):
            with open(meta_path, 'r', encoding='utf-8') as f:
                meta = json.load(f)
            meta['draft_cover'] = 'draft_cover.jpg'
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
        
        print(f'[封面] 已写入草稿: {draft_name}')
    else:
        print(f'[封面] 草稿不存在: {draft_name}')
        print(f'[封面] 封面图已保存到: {封面输出}')
    
    # 清理临时文件
    for tmp in [底图路径]:
        if os.path.exists(tmp):
            os.remove(tmp)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("用法: python generate_cover.py <项目路径> <草稿名> [--index N]")
        sys.exit(1)
    
    project_dir = os.path.abspath(sys.argv[1])
    draft_name = sys.argv[2]
    group_index = 1
    
    i = 3
    while i < len(sys.argv):
        if sys.argv[i] == '--index' and i + 1 < len(sys.argv):
            group_index = int(sys.argv[i + 1])
            i += 2
        else:
            i += 1
    
    generate_cover(project_dir, draft_name, group_index)
