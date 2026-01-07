#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
伯索云课堂课程下载器 - 打包脚本

使用方法:
    python build_exe.py

打包前请确保已安装所有依赖:
    pip install -r requirements.txt
"""

import os
import sys
import subprocess
import shutil

def install_dependencies():
    """安装依赖"""
    print("正在检查并安装依赖...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "--quiet"])
        print("依赖安装完成！")
        return True
    except subprocess.CalledProcessError as e:
        print(f"依赖安装失败: {e}")
        return False

def clean_build_dirs():
    """清理构建目录"""
    dirs_to_clean = ['build', 'dist']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"已清理 {dir_name} 目录")

def build_executable():
    """构建可执行文件"""
    print("开始构建可执行文件...")
    
    # 使用 PyInstaller 打包
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",          # 打包成单个文件
        "--windowed",         # 不显示控制台窗口
        "--name=伯索课程下载器",
        "--clean",            # 清理临时文件
        "--noupx",            # 不使用 UPX 压缩
        "main_gui.py"
    ]
    
    try:
        subprocess.check_call(cmd)
        print("\n" + "="*50)
        print("打包成功！")
        print("="*50)
        
        # 检查输出文件
        exe_path = os.path.join("dist", "伯索课程下载器.exe")
        if os.path.exists(exe_path):
            file_size = os.path.getsize(exe_path) / (1024 * 1024)
            print(f"\n输出文件: {exe_path}")
            print(f"文件大小: {file_size:.2f} MB")
            print("\n使用方法:")
            print("1. 双击 '伯索课程下载器.exe' 运行程序")
            print("2. 首次运行会在同级目录创建 config 文件夹")
            print("3. 下载的文件默认保存在 'downloads' 文件夹")
        else:
            print("警告: 未找到生成的可执行文件")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"打包失败: {e}")
        return False

def create_readme():
    """创建使用说明"""
    readme_content = """# 伯索云课堂课程下载器

## 软件简介

伯索云课堂课程下载器是一款用于下载伯索云课堂课程视频的工具软件，提供简洁的图形界面，支持批量下载、进度显示、历史记录等功能。

## 功能特点

- 简洁美观的白色主题界面
- 支持 Token 登录方式
- 课程列表浏览和搜索
- 章节查看和批量选择
- 实时下载进度显示
- 下载历史记录管理
- 自定义下载路径
- FFmpeg 集成支持

## 系统要求

- 操作系统: Windows 10/11 (推荐)
- 内存: 最低 512MB，推荐 2GB
- 硬盘: 至少 100MB 空间
- .NET Framework: 4.5 或更高版本

## 安装步骤

### 方法一: 使用预打包版本

1. 下载 `伯索课程下载器.exe`
2. 将文件保存到任意目录
3. 双击运行即可

### 方法二: 从源码运行

1. 安装 Python 3.8 或更高版本
2. 下载源码文件
3. 安装依赖:
   ```
   pip install -r requirements.txt
   ```
4. 运行程序:
   ```
   python main_gui.py
   ```

### 方法三: 打包成 EXE

1. 安装 Python 3.8 或更高版本
2. 下载源码文件
3. 安装依赖:
   ```
   pip install -r requirements.txt
   ```
4. 执行打包脚本:
   ```
   python build_exe.py
   ```
5. 打包完成后，EXE 文件位于 `dist` 目录

## 使用说明

### 1. 获取 Token

由于伯索云课堂的限制，需要通过以下方式获取 Token:

**方法一: 通过浏览器开发者工具**

1. 登录伯索云课堂网页版
2. 按 F12 打开开发者工具
3. 切换到 Network (网络) 标签
4. 刷新页面或点击任意课程
5. 找到包含 `access_token` 的请求
6. 复制完整的响应内容或 access_token 值

**方法二: 通过浏览器存储**

1. 登录伯索云课堂网页版
2. 打开浏览器控制台 (F12)
3. 输入以下代码:
   ```javascript
   localStorage.getItem('access_token')
   ```
4. 复制返回的 Token 值

### 2. 登录软件

1. 启动程序
2. 在左侧 Token 输入框中粘贴 Token 或完整的 HTTP 响应
3. 点击「登录」按钮
4. 登录成功后会自动加载课程列表

### 3. 下载课程

1. 在课程列表中点击「查看」进入章节页面
2. 勾选需要下载的章节（可使用全选功能）
3. 可点击路径输入框右侧的 📁 按钮修改保存位置
4. 点击「下载选中」开始下载
5. 下载过程中可查看实时进度

### 4. 设置说明

进入「系统设置」页面可以配置:

- **下载路径**: 设置默认保存位置
- **FFmpeg 路径**: 如果程序未自动检测到 FFmpeg，需手动选择
- **界面主题**: 支持浅色/深色两种主题

## 常见问题

### Q: 程序提示 "未检测到 FFmpeg" 怎么办?

A: FFmpeg 是视频处理的核心组件。请按以下步骤安装:

1. 下载 FFmpeg (https://ffmpeg.org/download.html)
2. 解压到任意目录
3. 将 bin 目录添加到系统 PATH 环境变量
4. 重启程序，或在设置中手动选择 ffmpeg.exe

### Q: 下载的视频无法播放?

A: 可能原因:

1. FFmpeg 未正确安装或配置
2. 视频源采用特殊加密格式
3. Token 已过期，需重新登录

### Q: 下载速度慢怎么办?

A: 建议:

1. 检查网络连接
2. 避开高峰时段下载
3. 确认 FFmpeg 已正确配置

### Q: 程序无法启动?

A: 尝试:

1. 安装 Visual C++ Redistributable
2. 以管理员身份运行
3. 检查杀毒软件是否拦截

## 卸载方法

1. 删除程序文件夹
2. 删除 config 文件夹（如有需要）
3. 删除 downloads 文件夹（如有需要）

## 注意事项

1. 本软件仅供个人学习使用
2. 请确保您有权下载相关课程内容
3. 下载后请及时备份，防止数据丢失
4. Token 有过期时间，过期后需重新获取

## 联系方式

如有问题或建议，请联系开发者。

## 更新日志

### v1.1 (2024-01)
- 优化跨平台兼容性
- 改进 FFmpeg 检测逻辑
- 修复多处已知问题
- 提升程序稳定性

### v1.0 (初始版本)
- 实现基本功能
- 白色简洁主题
- Token 登录
- 批量下载
- 历史记录
"""
    
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(readme_content)
    print("已创建使用说明文件 README.md")

def main():
    """主函数"""
    print("="*50)
    print("  伯索云课堂课程下载器 - 打包工具")
    print("="*50)
    print()
    
    # 检查是否在打包环境
    if not os.path.exists("main_gui.py"):
        print("错误: 未找到 main_gui.py 文件")
        return
    
    # 安装依赖
    if not install_dependencies():
        return
    
    # 清理旧文件
    clean_build_dirs()
    
    # 创建使用说明
    create_readme()
    
    # 构建可执行文件
    build_executable()

if __name__ == "__main__":
    main()
