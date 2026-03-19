#!/usr/bin/env python3
"""
论文图片提取工具
整合自 evil-read-arxiv 项目

功能：
- 从 PDF 提取图片
- 从 arXiv 源码包提取高质量图片
- 自动生成图片索引
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Optional
from urllib.request import urlopen, Request


def extract_images_from_pdf(
    pdf_path: Path,
    output_dir: Path,
    prefix: str = ""
) -> list[Path]:
    """
    从 PDF 提取图片
    
    Args:
        pdf_path: PDF 文件路径
        output_dir: 输出目录
        prefix: 文件名前缀
    
    Returns:
        list: 提取的图片路径列表
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    extracted = []
    
    # 尝试使用 PyMuPDF
    try:
        import fitz  # PyMuPDF
        
        doc = fitz.open(str(pdf_path))
        
        for page_num, page in enumerate(doc):
            images = page.get_images(full=True)
            
            for img_index, img in enumerate(images):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                
                # 保存图片
                filename = f"{prefix}_page{page_num + 1}_img{img_index + 1}.{image_ext}"
                img_path = output_dir / filename
                
                with open(img_path, 'wb') as f:
                    f.write(image_bytes)
                
                extracted.append(img_path)
        
        doc.close()
        print(f"[PDF] 提取了 {len(extracted)} 张图片")
        return extracted
    
    except ImportError:
        print("[PDF] PyMuPDF 未安装，尝试其他方法...")
    
    # 备选：使用 pdfimages 命令行工具
    if shutil.which("pdfimages"):
        output_prefix = output_dir / prefix
        result = subprocess.run(
            ["pdfimages", "-png", str(pdf_path), str(output_prefix)],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            # 收集生成的图片
            for f in output_dir.glob(f"{prefix}*.png"):
                extracted.append(f)
            print(f"[PDF] 使用 pdfimages 提取了 {len(extracted)} 张图片")
            return extracted
    
    print("[PDF] 无法提取图片（需要 PyMuPDF 或 pdfimages）")
    return []


def download_arxiv_source(
    arxiv_id: str,
    output_dir: Path
) -> Optional[Path]:
    """
    下载 arXiv 源码包
    
    Args:
        arxiv_id: arXiv ID
        output_dir: 输出目录
    
    Returns:
        Path: 源码包路径（如果成功）
    """
    # 清理 arXiv ID
    arxiv_id = re.sub(r'^ar[xX]iv[:\s]*', '', arxiv_id).strip()
    
    # 尝试下载源码包
    source_url = f"https://arxiv.org/e-print/{arxiv_id}"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    source_path = output_dir / f"{arxiv_id.replace('/', '_')}_source.tar.gz"
    
    try:
        print(f"[arXiv] 下载源码包: {arxiv_id}")
        
        req = Request(source_url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=60) as response:
            with open(source_path, 'wb') as f:
                f.write(response.read())
        
        print(f"[arXiv] 下载完成: {source_path}")
        return source_path
    
    except Exception as e:
        print(f"[arXiv] 下载失败: {e}")
        return None


def extract_images_from_source(
    source_path: Path,
    output_dir: Path,
    prefix: str = ""
) -> list[Path]:
    """
    从 arXiv 源码包提取图片
    
    Args:
        source_path: 源码包路径
        output_dir: 输出目录
        prefix: 文件名前缀
    
    Returns:
        list: 提取的图片路径列表
    """
    extracted = []
    
    # 创建临时目录
    temp_dir = output_dir / "temp_extract"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # 解压 tar.gz
        import tarfile
        
        with tarfile.open(source_path, 'r:gz') as tar:
            tar.extractall(temp_dir)
        
        # 查找图片文件
        image_extensions = {'.png', '.jpg', '.jpeg', '.pdf', '.eps', '.tif', '.tiff'}
        
        for f in temp_dir.rglob('*'):
            if f.suffix.lower() in image_extensions:
                # 复制到输出目录
                new_name = f"{prefix}_{f.stem}{f.suffix}"
                dest = output_dir / new_name
                
                shutil.copy2(f, dest)
                extracted.append(dest)
        
        print(f"[源码] 提取了 {len(extracted)} 张图片")
        
    except Exception as e:
        print(f"[源码] 解压失败: {e}")
    
    finally:
        # 清理临时目录
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    return extracted


def extract_paper_images(
    arxiv_id: str,
    output_dir: Path,
    prefer_source: bool = True
) -> list[Path]:
    """
    提取论文图片（优先从源码包）
    
    Args:
        arxiv_id: arXiv ID
        output_dir: 输出目录
        prefer_source: 是否优先从源码包提取
    
    Returns:
        list: 图片路径列表
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = arxiv_id.replace('/', '_')
    
    extracted = []
    
    # 1. 尝试从源码包提取（质量更高）
    if prefer_source:
        source_path = download_arxiv_source(arxiv_id, output_dir)
        if source_path:
            extracted = extract_images_from_source(source_path, output_dir, prefix)
            
            # 删除源码包
            source_path.unlink(missing_ok=True)
    
    # 2. 如果源码包提取失败，从 PDF 提取
    if not extracted:
        # 下载 PDF
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        pdf_path = output_dir / f"{prefix}.pdf"
        
        try:
            print(f"[PDF] 下载: {arxiv_id}")
            
            req = Request(pdf_url, headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(req, timeout=60) as response:
                with open(pdf_path, 'wb') as f:
                    f.write(response.read())
            
            # 提取图片
            extracted = extract_images_from_pdf(pdf_path, output_dir, prefix)
            
            # 删除 PDF（可选）
            # pdf_path.unlink(missing_ok=True)
            
        except Exception as e:
            print(f"[PDF] 下载失败: {e}")
    
    return extracted


def generate_image_index(
    images: list[Path],
    output_file: Path,
    paper_title: str = ""
) -> None:
    """
    生成图片索引 Markdown 文件
    
    Args:
        images: 图片路径列表
        output_file: 输出文件路径
        paper_title: 论文标题
    """
    lines = [f"# 图片索引", ""]
    
    if paper_title:
        lines.append(f"**论文：** {paper_title}")
        lines.append("")
    
    lines.append(f"**图片数量：** {len(images)}")
    lines.append("")
    lines.append("## 图片列表")
    lines.append("")
    
    for i, img in enumerate(images, 1):
        rel_path = img.name
        lines.append(f"### 图{i}: {img.stem}")
        lines.append("")
        lines.append(f"![{img.stem}]({rel_path})")
        lines.append("")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print(f"[索引] 生成: {output_file}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="提取论文图片")
    parser.add_argument("--arxiv-id", required=True, help="arXiv ID")
    parser.add_argument("--output", default="images", help="输出目录")
    parser.add_argument("--title", default="", help="论文标题")
    parser.add_argument("--no-source", action="store_true", help="不从源码包提取")
    
    args = parser.parse_args()
    
    output_dir = Path(args.output)
    images = extract_paper_images(
        args.arxiv_id,
        output_dir,
        prefer_source=not args.no_source
    )
    
    if images:
        # 生成索引
        index_file = output_dir / "image_index.md"
        generate_image_index(images, index_file, args.title)
        
        print(f"\n提取完成:")
        print(f"  图片目录: {output_dir}")
        print(f"  图片数量: {len(images)}")
        print(f"  索引文件: {index_file}")
