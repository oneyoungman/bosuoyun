#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
伯索云课堂课程下载器 - 白色简洁风格 GUI 版本
使用 CustomTkinter 实现现代化界面

功能特点:
1. 白色简洁 UI 设计
2. 实时下载进度条
3. Token 输入/登录/退出
4. 批量下载管理
5. 下载历史记录
6. 设置管理

依赖安装:
    pip install customtkinter httpx pyinstaller

打包命令:
    pyinstaller --onefile --windowed --name "伯索课程下载器" --add-data "config;config" main_gui.py
"""

import os
import sys
import json
import asyncio
import threading
import subprocess
import time
import re
import webbrowser
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox
import tkinter as tk

# 尝试导入 CustomTkinter，如果失败则使用备用方案
try:
    import customtkinter as ctk
    USE_MODERN_UI = True
except ImportError:
    USE_MODERN_UI = False
    import tkinter.ttk as ttk


# ============== 白色简洁主题配置 ==============

class ThemeManager:
    """主题管理器 - 白色简洁风格"""

    # 白色主题配色
    LIGHT_THEME = {
        "bg_primary": "#f5f5f7",
        "bg_secondary": "#ffffff",
        "bg_tertiary": "#f0f0f5",
        "accent": "#007AFF",
        "accent_hover": "#0056CC",
        "accent_light": "#E8F0FE",
        "text_primary": "#1d1d1f",
        "text_secondary": "#86868b",
        "text_disabled": "#a1a1a6",
        "success": "#34C759",
        "warning": "#FF9500",
        "error": "#FF3B30",
        "border": "#e5e5ea",
        "card_bg": "#ffffff",
        "shadow": "#00000010",
    }

    # 深色主题配色（备用）
    DARK_THEME = {
        "bg_primary": "#1a1a2e",
        "bg_secondary": "#16213e",
        "bg_tertiary": "#0f3460",
        "accent": "#007AFF",
        "accent_hover": "#5AC8FA",
        "accent_light": "#0f3460",
        "text_primary": "#ffffff",
        "text_secondary": "#a0a0a0",
        "text_disabled": "#666666",
        "success": "#34C759",
        "warning": "#FF9500",
        "error": "#FF3B30",
        "border": "#2a2a4a",
        "card_bg": "#1f1f3a",
        "shadow": "#00000030",
    }

    @classmethod
    def get_colors(cls, theme_name="light"):
        """获取主题颜色"""
        if theme_name == "dark":
            return cls.DARK_THEME
        return cls.LIGHT_THEME


# ============== API 客户端 ==============

class PlasoAPIClient:
    """伯索云课堂 API 客户端"""

    def __init__(self, access_token: str = None):
        self.base_url = "https://www.plaso.cn"
        self.access_token = access_token

    def set_token(self, access_token: str):
        self.access_token = access_token

    def _get_headers(self) -> dict:
        return {
            "access-token": self.access_token,
            "device": "pc",
            "version": "5.62.327",
            "platform": "plaso",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36",
            "Content-Type": "application/json",
            "Accept": "*/*",
        }

    async def get_course_list(self) -> list:
        """获取课程列表"""
        import httpx
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self.base_url}/course/api/v1/m/package/student/list"
                headers = self._get_headers()
                response = await client.post(url, headers=headers, json={"search": ""})

                if response.status_code == 200:
                    result = response.json()
                    if result.get("code") == 0:
                        return result.get("obj", [])
                return []
        except Exception as e:
            print(f"获取课程失败: {e}")
            return []

    async def get_task_list(self, x_file_id: str, dir_id: str) -> list:
        """获取任务列表"""
        import httpx
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self.base_url}/yxt/servlet/bigDir/getXfgTask"
                headers = self._get_headers()
                json_data = {
                    "hiddenTask": 1,
                    "sourceWay": 1,
                    "needMyFav": True,
                    "id": dir_id,
                    "needProgress": True,
                    "xFileId": x_file_id
                }
                response = await client.post(url, headers=headers, json=json_data)

                if response.status_code == 200:
                    result = response.json()
                    if result.get("code") == 0:
                        return result.get("obj", [])
                return []
        except Exception as e:
            print(f"获取任务失败: {e}")
            return []

    def validate_token(self) -> dict:
        """验证 Token 并获取用户信息"""
        import httpx
        try:
            url = f"{self.base_url}/course/api/v1/m/package/student/list"
            headers = self._get_headers()

            response = httpx.post(url, headers=headers, json={"search": ""}, timeout=10)

            if response.status_code == 200:
                result = response.json()
                if result.get("code") == 0:
                    return {"success": True, "user_info": result.get("obj")}

            return {"success": False, "message": "Token 验证失败"}
        except Exception as e:
            return {"success": False, "message": str(e)}


# ============== 配置管理 ==============

class ConfigManager:
    """配置管理器"""

    def __init__(self):
        # 优先使用应用程序目录，兼容打包后的环境
        if getattr(sys, 'frozen', False):
            # 打包后的应用程序
            app_dir = Path(sys.executable).parent
            self.config_dir = app_dir / "config"
        else:
            # 开发环境
            self.config_dir = Path("./config")
        
        self.config_dir.mkdir(exist_ok=True)
        self.config_file = self.config_dir / "settings.json"
        self.token_file = self.config_dir / "token.json"
        self.history_file = self.config_dir / "history.json"

        self.settings = self.load_settings()
        self.token = self.load_token()
        self.history = self.load_history()

    def load_settings(self) -> dict:
        """加载设置"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {
            "download_path": str(Path("./downloads")),
            "ffmpeg_path": "",
            "theme": "light",
            "max_concurrent": 1
        }

    def save_settings(self, settings: dict):
        """保存设置"""
        self.settings.update(settings)
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.settings, f, ensure_ascii=False, indent=2)

    def load_token(self) -> dict:
        """加载 Token"""
        if self.token_file.exists():
            try:
                with open(self.token_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}

    def save_token(self, token_data: dict):
        """保存 Token"""
        self.token = token_data
        with open(self.token_file, 'w', encoding='utf-8') as f:
            json.dump(token_data, f, ensure_ascii=False, indent=2)

    def clear_token(self):
        """清除 Token"""
        self.token = {}
        if self.token_file.exists():
            self.token_file.unlink()

    def load_history(self) -> list:
        """加载下载历史"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return []

    def add_history(self, item: dict):
        """添加历史记录"""
        self.history.insert(0, item)
        # 只保留最近 100 条
        self.history = self.history[:100]
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)


# ============== 下载器核心 ==============

class DownloadManager:
    """下载管理器"""

    def __init__(self, config: ConfigManager):
        self.config = config
        self.ffmpeg_path = None
        self.find_ffmpeg()

    def find_ffmpeg(self):
        """查找 FFmpeg"""
        # 常见位置 - 跨平台支持
        common_paths = []
        
        # 添加Windows常见路径
        if os.name == 'nt':
            common_paths.extend([
                "D:\\project_software\\ffmpeg-8.0.1-essentials_build\\bin\\ffmpeg.exe",
                "D:\\ffmpeg\\bin\\ffmpeg.exe",
                "C:\\ffmpeg\\bin\\ffmpeg.exe",
            ])
        
        # 添加当前目录和PATH中的查找
        common_paths.extend([
            "ffmpeg",
            "ffmpeg.exe",
        ])

        # 先检查配置中的路径
        if self.config.settings.get("ffmpeg_path"):
            path = self.config.settings["ffmpeg_path"]
            if Path(path).exists():
                self.ffmpeg_path = str(Path(path))
                return

        for path in common_paths:
            if Path(path).exists():
                self.ffmpeg_path = str(Path(path))
                return

        # 尝试在系统 PATH 中查找
        try:
            if os.name == 'nt':
                result = subprocess.run(["where", "ffmpeg"], capture_output=True, text=True, shell=True)
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    if lines:
                        self.ffmpeg_path = lines[0]
                        return
            else:
                result = subprocess.run(["which", "ffmpeg"], capture_output=True, text=True)
                if result.returncode == 0:
                    self.ffmpeg_path = result.stdout.strip()
                    return
        except:
            pass

        self.ffmpeg_path = None

    def download_video(self, m3u8_url: str, output_path: str,
                       progress_callback=None, finished_callback=None) -> bool:
        """下载视频"""
        if not self.ffmpeg_path:
            if finished_callback:
                finished_callback(False, "未找到 FFmpeg")
            return False

        try:
            output_path = str(Path(output_path))
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            cmd = [
                self.ffmpeg_path,
                "-i", m3u8_url,
                "-c", "copy",
                "-bsf:a", "aac_adtstoasc",
                "-y",
                output_path
            ]

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1
            )

            duration = None
            start_time = time.time()

            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break

                # 解析进度
                if "Duration:" in line:
                    match = re.search(r'Duration: (\d+):(\d+):(\d+)', line)
                    if match:
                        h, m, s = map(int, match.groups())
                        duration = h * 3600 + m * 60 + s

                if "time=" in line and duration:
                    match = re.search(r'time= (\d+):(\d+):(\d+)', line)
                    if match:
                        h, m, s = map(int, match.groups())
                        current = h * 3600 + m * 60 + s
                        progress = (current / duration) * 100

                        if progress_callback:
                            progress_callback(progress)

            process.wait()

            if process.returncode == 0 and Path(output_path).exists():
                file_size = Path(output_path).stat().st_size / (1024 * 1024)
                if finished_callback:
                    finished_callback(True, f"{file_size:.1f}MB")
                return True
            else:
                if finished_callback:
                    finished_callback(False, "下载失败")
                return False

        except Exception as e:
            print(f"下载错误: {e}")
            if finished_callback:
                finished_callback(False, str(e))
            return False


# ============== UI 组件 ==============

def safe_filename(name):
    """生成安全的文件名"""
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = name.strip()
    return name[:50]


class ModernCourseCard:
    """现代化课程卡片 - 白色简洁风格"""

    def __init__(self, parent, task, index, on_check_changed, on_path_changed, default_path, colors=None):
        self.parent = parent
        self.task = task
        self.on_check_changed = on_check_changed
        self.on_path_changed = on_path_changed
        self.checked = False
        self.colors = colors or ThemeManager.LIGHT_THEME

        task_id = task.get("_id", "")
        task_name = task.get("name", f"章节 {index + 1}")
        record_files = task.get("recordFiles", [])
        has_video = len(record_files) > 0

        # 简洁白色卡片样式
        self.card_frame = ctk.CTkFrame(
            parent,
            corner_radius=8,
            fg_color=self.colors["bg_secondary"],
            border_width=1,
            border_color=self.colors["border"]
        )
        self.card_frame.pack(fill="x", padx=8, pady=3)

        # 复选框 - 蓝色主题
        self.checkbox = ctk.CTkCheckBox(
            self.card_frame,
            text="",
            command=self.on_check,
            width=28,
            fg_color=self.colors["accent"],
            hover_color=self.colors["accent_hover"],
            border_color=self.colors["text_disabled"],
            border_width=2
        )
        self.checkbox.pack(side="left", padx=(10, 5), pady=10)

        # 编号
        ctk.CTkLabel(
            self.card_frame,
            text=f"{index + 1}",
            font=("Microsoft YaHei", 10),
            width=25,
            text_color=self.colors["text_disabled"]
        ).pack(side="left")

        # 标题 - 黑色主要文字
        title_label = ctk.CTkLabel(
            self.card_frame,
            text=task_name,
            font=("Microsoft YaHei", 11),
            width=280,
            anchor="w",
            text_color=self.colors["text_primary"]
        )
        title_label.pack(side="left", padx=8)

        # 进度条 - 绿色主题
        self.progress = ctk.CTkProgressBar(
            self.card_frame,
            width=140,
            progress_color=self.colors["success"],
            fg_color=self.colors["bg_tertiary"]
        )
        self.progress.set(0)
        self.progress.pack(side="left", padx=8)

        # 状态 - 灰色次要文字
        self.status_label = ctk.CTkLabel(
            self.card_frame,
            text="等待",
            font=("Microsoft YaHei", 10),
            width=70,
            text_color=self.colors["text_secondary"]
        )
        self.status_label.pack(side="left", padx=5)

        # 路径输入框 - 简洁风格
        self.path_var = ctk.StringVar(value=str(default_path / f"{safe_filename(task_name)}.mp4"))
        path_entry = ctk.CTkEntry(
            self.card_frame,
            textvariable=self.path_var,
            width=240,
            font=("Consolas", 9),
            fg_color=self.colors["bg_tertiary"],
            text_color=self.colors["text_primary"],
            border_color=self.colors["border"],
            border_width=1,
            corner_radius=4
        )
        path_entry.pack(side="left", padx=5)

        # 选择文件夹按钮 - 简洁图标按钮
        browse_btn = ctk.CTkButton(
            self.card_frame,
            text="",
            width=28,
            height=28,
            command=self.browse_folder,
            fg_color=self.colors["bg_tertiary"],
            hover_color=self.colors["accent_light"],
            border_width=0,
            corner_radius=4
        )
        browse_btn.pack(side="left", padx=(3, 8))

        # 文件夹图标
        ctk.CTkLabel(
            browse_btn,
            text="📁",
            font=("Microsoft YaHei", 12)
        ).place(relx=0.5, rely=0.5, anchor="center")

        # 保存引用
        self.card_frame.task_id = task_id
        self.card_frame.task_data = task
        self.card_frame.has_video = has_video
        self.card_frame.status_label = self.status_label
        self.card_frame.progress = self.progress

    def on_check(self):
        """复选框点击事件"""
        self.checked = not self.checked
        if self.checked:
            self.checkbox.select()
        else:
            self.checkbox.deselect()
        if self.on_check_changed:
            self.on_check_changed()

    def is_checked(self):
        """返回选中状态"""
        return self.checked

    def set_checked(self, value):
        """设置选中状态"""
        self.checked = value
        if value:
            self.checkbox.select()
        else:
            self.checkbox.deselect()

    def browse_folder(self):
        folder = filedialog.askdirectory(title="选择保存位置")
        if folder:
            filename = Path(self.path_var.get()).name
            self.path_var.set(str(Path(folder) / filename))
            if self.on_path_changed:
                self.on_path_changed()

    def update_status(self, text, color=None):
        """更新状态文本和颜色"""
        if color is None:
            color = self.colors["text_secondary"]
        self.status_label.configure(text=text, text_color=color)

    def set_progress(self, value):
        self.progress.set(value / 100)


# ============== 主界面 ==============

class BersoDownloaderApp:
    """主应用程序 - 白色简洁风格"""

    def __init__(self):
        # 初始化配置
        self.config = ConfigManager()

        # 获取当前主题颜色 - 默认使用浅色
        self.theme_name = self.config.settings.get("theme", "light")
        self.colors = ThemeManager.get_colors(self.theme_name)

        # 初始化下载器
        self.download_manager = DownloadManager(self.config)

        # 状态变量
        self.client = None
        self.courses = []
        self.current_course = None
        self.download_tasks = []
        self.downloading = False
        self.course_cards = []
        self.current_page = "courses"

        # 创建窗口
        if USE_MODERN_UI:
            self.setup_modern_ui()
        else:
            self.setup_classic_ui()

    def setup_modern_ui(self):
        """设置现代化 UI - 白色简洁风格"""
        # 设置主题
        ctk.set_appearance_mode(self.theme_name)
        ctk.set_default_color_theme("blue")

        # 创建主窗口
        self.root = ctk.CTk()
        self.root.title("伯索云课堂课程下载器 v1.1")
        self.root.geometry("1150x720")
        self.root.minsize(1000, 580)
        
        # 设置窗口图标（如果存在）
        icon_path = self.get_icon_path()
        if icon_path and os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except:
                pass

        # 配置网格
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        # 创建侧边栏
        self.create_sidebar()

        # 创建主内容区
        self.create_main_area()

        # 尝试自动登录
        self.try_auto_login()

    def get_icon_path(self):
        """获取图标路径"""
        if getattr(sys, 'frozen', False):
            base_dir = Path(sys.executable).parent
        else:
            base_dir = Path(__file__).parent
        
        possible_icons = [
            base_dir / "icon.ico",
            base_dir / "app.ico",
            base_dir / "favicon.ico",
        ]
        
        for icon in possible_icons:
            if icon.exists():
                return str(icon)
        return None

    def create_sidebar(self):
        """创建侧边栏 - 白色简洁风格"""
        self.sidebar = ctk.CTkFrame(
            self.root,
            width=220,
            corner_radius=0,
            fg_color=self.colors["bg_secondary"],
            border_width=0
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        # Logo区域
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent", corner_radius=0)
        logo_frame.pack(fill="x", pady=0)

        ctk.CTkLabel(
            logo_frame,
            text="🎓",
            font=("Microsoft YaHei", 28)
        ).pack(pady=(20, 5))

        ctk.CTkLabel(
            logo_frame,
            text="伯索下载器",
            font=("Microsoft YaHei", 16, "bold"),
            text_color=self.colors["text_primary"]
        ).pack(pady=(0, 5))

        ctk.CTkLabel(
            logo_frame,
            text="v1.1",
            font=("Microsoft YaHei", 9),
            text_color=self.colors["text_disabled"]
        ).pack(pady=(0, 15))

        # Token输入区域 - 新设计
        token_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        token_frame.pack(fill="x", padx=12, pady=5)

        ctk.CTkLabel(
            token_frame,
            text="Token 登录",
            font=("Microsoft YaHei", 10, "bold"),
            text_color=self.colors["text_secondary"]
        ).pack(anchor="w", pady=(0, 5))

        # Token输入框
        self.token_entry = ctk.CTkTextbox(
            token_frame,
            width=196,
            height=60,
            font=("Consolas", 9),
            fg_color=self.colors["bg_tertiary"],
            text_color=self.colors["text_primary"],
            border_color=self.colors["border"],
            border_width=1,
            corner_radius=6
        )
        self.token_entry.pack(fill="x", pady=(0, 5))
        self.token_entry.insert("1.0", "粘贴HTTP响应或token...")
        self.token_entry.bind("<FocusIn>", self.on_token_focus_in)
        self.token_entry.bind("<FocusOut>", self.on_token_focus_out)

        # 登录按钮
        self.login_btn = ctk.CTkButton(
            token_frame,
            text="登录",
            command=self.login_with_token,
            height=32,
            corner_radius=6,
            fg_color=self.colors["accent"],
            hover_color=self.colors["accent_hover"],
            font=("Microsoft YaHei", 11, "bold")
        )
        self.login_btn.pack(fill="x")

        # 退出登录按钮（初始隐藏）
        self.logout_btn = ctk.CTkButton(
            token_frame,
            text="退出登录",
            command=self.logout,
            height=32,
            corner_radius=6,
            fg_color=self.colors["bg_tertiary"],
            hover_color=self.colors["error"],
            text_color=self.colors["text_primary"],
            font=("Microsoft YaHei", 11)
        )
        self.logout_btn.pack(fill="x", pady=5)
        self.logout_btn.pack_forget()

        # 用户信息显示
        self.user_info_label = ctk.CTkLabel(
            token_frame,
            text="",
            font=("Microsoft YaHei", 10),
            text_color=self.colors["text_secondary"],
            wraplength=180
        )
        self.user_info_label.pack(pady=8)

        # 分隔线
        ctk.CTkFrame(
            self.sidebar,
            height=1,
            fg_color=self.colors["border"]
        ).pack(fill="x", padx=15, pady=12)

        # 菜单按钮 - 简洁风格
        self.menu_buttons = []
        menu_items = [
            ("📚 我的课程", self.show_courses),
            ("📥 下载管理", self.show_downloads),
            ("📜 下载历史", self.show_history),
            ("⚙️ 系统设置", self.show_settings)
        ]

        for i, (text, command) in enumerate(menu_items):
            btn = ctk.CTkButton(
                self.sidebar,
                text=text,
                command=command,
                height=38,
                corner_radius=6,
                fg_color="transparent",
                border_width=0,
                text_color=(self.colors["text_primary"], self.colors["text_primary"]),
                hover_color=self.colors["bg_tertiary"],
                font=("Microsoft YaHei", 11),
                anchor="w"
            )
            btn.pack(fill="x", padx=12, pady=2)
            self.menu_buttons.append(btn)

        # 底部状态栏
        bottom_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        bottom_frame.pack(side="bottom", fill="x", padx=15, pady=15)

        # FFmpeg 状态
        self.ffmpeg_status = ctk.CTkLabel(
            bottom_frame,
            text="FFmpeg: 检测中...",
            font=("Microsoft YaHei", 9),
            text_color=self.colors["text_disabled"]
        )
        self.ffmpeg_status.pack(anchor="w")

        self.check_ffmpeg_status()

    def on_token_focus_in(self, event):
        """Token输入框获得焦点"""
        if self.token_entry.get("1.0", "end").strip() == "粘贴HTTP响应或token...":
            self.token_entry.delete("1.0", "end")

    def on_token_focus_out(self, event):
        """Token输入框失去焦点"""
        if self.token_entry.get("1.0", "end").strip() == "":
            self.token_entry.insert("1.0", "粘贴HTTP响应或token...")

    def parse_token_from_response(self, content):
        """从HTTP响应或文本中解析token"""
        # 尝试直接匹配 access_token
        token_match = re.search(r'"access_token":"([^"]+)"', content)
        if token_match:
            return token_match.group(1)

        # 尝试从原始token字符串匹配
        if re.match(r'^\d{5}-\d-\d+-[a-f0-9]+-\d+-[^"]+$', content.strip()):
            return content.strip()

        return None

    def login_with_token(self):
        """使用输入的token登录"""
        content = self.token_entry.get("1.0", "end").strip()

        if not content or content == "粘贴HTTP响应或token...":
            messagebox.showwarning("提示", "请输入或粘贴 Token！\n\n支持直接粘贴 HTTP 响应文本或纯 token 字符串")
            return

        # 解析token
        token = self.parse_token_from_response(content)

        if not token:
            messagebox.showerror("错误", "无法从输入中解析出有效的 Token！\n\n请确保输入包含 access_token 字段")
            return

        # 验证 Token
        self.client = PlasoAPIClient(token)
        result = self.client.validate_token()

        if result["success"]:
            user_info = result.get("user_info", {})
            name = user_info.get("name", "用户")
            org_name = user_info.get("myOrg", {}).get("name", "")

            token_data = {
                "access_token": token,
                "user_info": user_info
            }
            self.config.save_token(token_data)
            self.update_login_state(True, token_data)
            self.refresh_courses()
            messagebox.showinfo("登录成功", f"欢迎回来，{name}！\n机构：{org_name}")
        else:
            messagebox.showerror("登录失败", "Token 验证失败，请检查输入是否正确！")

    def create_main_area(self):
        """创建主内容区 - 白色简洁风格"""
        self.main_frame = ctk.CTkFrame(
            self.root,
            corner_radius=0,
            fg_color=self.colors["bg_primary"]
        )
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)

        # 顶部栏 - 简洁白色
        self.top_bar = ctk.CTkFrame(
            self.main_frame,
            height=56,
            corner_radius=0,
            fg_color=self.colors["bg_secondary"],
            border_width=0
        )
        self.top_bar.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        self.top_bar.grid_propagate(False)

        # 页面标题 - 黑色主要文字
        self.page_title = ctk.CTkLabel(
            self.top_bar,
            text="我的课程",
            font=("Microsoft YaHei", 16, "bold"),
            text_color=self.colors["text_primary"]
        )
        self.page_title.pack(side="left", padx=20)

        # 刷新按钮 - 简洁按钮
        self.refresh_btn = ctk.CTkButton(
            self.top_bar,
            text="刷新",
            command=self.refresh_courses,
            width=70,
            height=30,
            fg_color=self.colors["bg_tertiary"],
            hover_color=self.colors["accent_light"],
            text_color=self.colors["text_primary"],
            border_width=0,
            corner_radius=6,
            font=("Microsoft YaHei", 10)
        )
        self.refresh_btn.pack(side="right", padx=20)

        # 内容容器
        self.content_frame = ctk.CTkFrame(
            self.main_frame,
            corner_radius=0,
            fg_color="transparent"
        )
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)

        # 默认显示课程页面
        self.show_courses()

    def show_courses(self):
        """显示课程页面"""
        self.current_page = "courses"
        self.page_title.configure(text="我的课程")

        # 更新菜单按钮状态
        self.update_menu_state(0)

        # 清除内容
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        # 搜索框区域 - 简洁卡片
        search_frame = ctk.CTkFrame(
            self.content_frame,
            height=56,
            corner_radius=8,
            fg_color=self.colors["bg_secondary"],
            border_width=1,
            border_color=self.colors["border"]
        )
        search_frame.pack(fill="x", padx=15, pady=12)
        search_frame.pack_propagate(False)

        # 搜索容器
        search_inner = ctk.CTkFrame(search_frame, fg_color="transparent")
        search_inner.pack(fill="x", padx=12, pady=8)

        ctk.CTkLabel(
            search_inner,
            text="搜索课程",
            font=("Microsoft YaHei", 10),
            text_color=self.colors["text_secondary"]
        ).pack(side="left")

        self.search_entry = ctk.CTkEntry(
            search_inner,
            width=300,
            placeholder_text="输入课程名称快速搜索...",
            font=("Microsoft YaHei", 10),
            fg_color=self.colors["bg_tertiary"],
            text_color=self.colors["text_primary"],
            border_color=self.colors["border"],
            border_width=1,
            corner_radius=4
        )
        self.search_entry.pack(side="left", padx=8)
        self.search_entry.bind("<KeyRelease>", self.filter_courses)

        # 课程统计
        self.course_count_label = ctk.CTkLabel(
            search_inner,
            text="",
            font=("Microsoft YaHei", 10),
            text_color=self.colors["text_disabled"]
        )
        self.course_count_label.pack(side="right", padx=5)

        # 课程列表容器 - 简洁卡片
        list_container = ctk.CTkFrame(
            self.content_frame,
            corner_radius=8,
            fg_color=self.colors["bg_secondary"],
            border_width=1,
            border_color=self.colors["border"]
        )
        list_container.pack(fill="both", expand=True, padx=15, pady=(0, 12))

        # 表头 - 简洁风格
        header_frame = ctk.CTkFrame(list_container, fg_color="transparent", height=40)
        header_frame.pack(fill="x", padx=12, pady=(10, 0))

        ctk.CTkLabel(
            header_frame,
            text="课程",
            font=("Microsoft YaHei", 10, "bold"),
            width=420,
            anchor="w",
            text_color=self.colors["text_secondary"]
        ).pack(side="left", padx=5)

        ctk.CTkLabel(
            header_frame,
            text="进度",
            font=("Microsoft YaHei", 10, "bold"),
            width=120,
            text_color=self.colors["text_secondary"]
        ).pack(side="left")

        ctk.CTkLabel(
            header_frame,
            text="章节",
            font=("Microsoft YaHei", 10, "bold"),
            width=80,
            text_color=self.colors["text_secondary"]
        ).pack(side="left")

        ctk.CTkLabel(
            header_frame,
            text="操作",
            font=("Microsoft YaHei", 10, "bold"),
            width=100,
            text_color=self.colors["text_secondary"]
        ).pack(side="left")

        # 分隔线
        ctk.CTkFrame(
            list_container,
            height=1,
            fg_color=self.colors["border"]
        ).pack(fill="x", padx=12, pady=8)

        # 可滚动区域
        self.course_scroll = ctk.CTkScrollableFrame(
            list_container,
            label_text="",
            fg_color="transparent"
        )
        self.course_scroll.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # 加载课程
        if self.client:
            self.display_courses()
        else:
            # 未登录状态
            self.show_login_prompt()

    def show_login_prompt(self):
        """显示登录提示"""
        for widget in self.course_scroll.winfo_children():
            widget.destroy()

        # 提示卡片 - 简洁风格
        prompt_card = ctk.CTkFrame(
            self.course_scroll,
            corner_radius=8,
            fg_color=self.colors["bg_tertiary"]
        )
        prompt_card.pack(fill="x", padx=10, pady=15)

        ctk.CTkLabel(
            prompt_card,
            text="🔐",
            font=("Microsoft YaHei", 32)
        ).pack(pady=(20, 10))

        ctk.CTkLabel(
            prompt_card,
            text="请先登录账号",
            font=("Microsoft YaHei", 13, "bold"),
            text_color=self.colors["text_primary"]
        ).pack()

        ctk.CTkLabel(
            prompt_card,
            text="在左侧输入框粘贴 Token 或 HTTP 响应后点击登录",
            font=("Microsoft YaHei", 10),
            text_color=self.colors["text_secondary"]
        ).pack(pady=(5, 15))

    def display_courses(self):
        """显示课程列表"""
        for widget in self.course_scroll.winfo_children():
            widget.destroy()

        if not self.courses:
            ctk.CTkLabel(
                self.course_scroll,
                text="暂无课程",
                font=("Microsoft YaHei", 12),
                text_color=self.colors["text_secondary"]
            ).pack(pady=20)
            self.course_count_label.configure(text="0 门课程")
            return

        # 更新课程统计
        self.course_count_label.configure(text=f"{len(self.courses)} 门")

        for course in self.courses:
            self.create_course_item(course)

    def create_course_item(self, course):
        """创建课程项 - 简洁风格"""
        card = ctk.CTkFrame(
            self.course_scroll,
            corner_radius=6,
            fg_color="transparent"
        )
        card.pack(fill="x", padx=8, pady=2)

        title = course.get("title", "未知课程")
        progress = course.get("progressRate", 0)
        task_num = course.get("taskNum", 0)

        # 课程名称
        ctk.CTkLabel(
            card,
            text=title,
            font=("Microsoft YaHei", 11),
            width=420,
            anchor="w",
            text_color=self.colors["text_primary"]
        ).pack(side="left", padx=8)

        # 进度
        progress_container = ctk.CTkFrame(card, fg_color="transparent", width=120)
        progress_container.pack(side="left")
        progress_container.pack_propagate(False)

        progress_bar = ctk.CTkProgressBar(
            progress_container,
            width=70,
            progress_color=self.colors["success"],
            fg_color=self.colors["bg_tertiary"]
        )
        progress_bar.place(relx=0, rely=0.5, anchor="w")
        progress_bar.set(progress / 100)

        ctk.CTkLabel(
            progress_container,
            text=f"{progress}%",
            font=("Microsoft YaHei", 9),
            width=30,
            text_color=self.colors["text_secondary"]
        ).place(relx=1, rely=0.5, anchor="e")

        # 章节数
        ctk.CTkLabel(
            card,
            text=f"{task_num}",
            font=("Microsoft YaHei", 11),
            width=80,
            text_color=self.colors["text_secondary"]
        ).pack(side="left")

        # 查看章节按钮 - 简洁蓝色按钮
        ctk.CTkButton(
            card,
            text="查看",
            width=80,
            height=28,
            command=lambda: self.show_chapters(course),
            fg_color=self.colors["accent"],
            hover_color=self.colors["accent_hover"],
            text_color="white",
            corner_radius=4,
            font=("Microsoft YaHei", 10)
        ).pack(side="left", padx=8)

    def filter_courses(self, event=None):
        """搜索过滤课程"""
        keyword = self.search_entry.get().lower()

        for widget in self.course_scroll.winfo_children():
            widget.destroy()

        filtered = []
        for course in self.courses:
            title = course.get("title", "").lower()
            if keyword in title:
                filtered.append(course)

        if not filtered:
            ctk.CTkLabel(
                self.course_scroll,
                text="未找到匹配的课程",
                font=("Microsoft YaHei", 12),
                text_color=self.colors["text_secondary"]
            ).pack(pady=20)
            self.course_count_label.configure(text="0 门")
            return

        self.course_count_label.configure(text=f"{len(filtered)} 门")

        for course in filtered:
            self.create_course_item(course)

    def show_chapters(self, course):
        """显示章节页面"""
        self.current_course = course
        self.current_page = "chapters"
        self.page_title.configure(text="章节列表")

        # 更新菜单按钮状态
        self.update_menu_state(0)

        # 清除内容
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        # 顶部工具栏 - 简洁卡片
        toolbar = ctk.CTkFrame(
            self.content_frame,
            height=56,
            corner_radius=8,
            fg_color=self.colors["bg_secondary"],
            border_width=1,
            border_color=self.colors["border"]
        )
        toolbar.pack(fill="x", padx=15, pady=12)
        toolbar.pack_propagate(False)

        # 返回按钮
        back_btn = ctk.CTkButton(
            toolbar,
            text="返回",
            width=70,
            height=30,
            command=self.show_courses,
            fg_color=self.colors["bg_tertiary"],
            hover_color=self.colors["accent_light"],
            text_color=self.colors["text_primary"],
            corner_radius=4,
            font=("Microsoft YaHei", 10)
        )
        back_btn.pack(side="left", padx=12)

        # 全选/取消全选
        select_all_btn = ctk.CTkButton(
            toolbar,
            text="全选",
            width=60,
            height=30,
            command=self.select_all_chapters,
            fg_color=self.colors["bg_tertiary"],
            hover_color=self.colors["accent_light"],
            text_color=self.colors["text_primary"],
            corner_radius=4,
            font=("Microsoft YaHei", 10)
        )
        select_all_btn.pack(side="left", padx=5)

        deselect_all_btn = ctk.CTkButton(
            toolbar,
            text="取消",
            width=60,
            height=30,
            command=self.deselect_all_chapters,
            fg_color=self.colors["bg_tertiary"],
            hover_color=self.colors["bg_tertiary"],
            text_color=self.colors["text_secondary"],
            corner_radius=4,
            font=("Microsoft YaHei", 10)
        )
        deselect_all_btn.pack(side="left", padx=5)

        # 已选择数量
        self.selected_count = ctk.CTkLabel(
            toolbar,
            text="已选择 0 个",
            font=("Microsoft YaHei", 10),
            text_color=self.colors["text_secondary"]
        )
        self.selected_count.pack(side="left", padx=15)

        # 下载选中按钮 - 绿色按钮
        self.download_selected_btn = ctk.CTkButton(
            toolbar,
            text="下载选中",
            width=100,
            height=32,
            command=self.start_batch_download,
            fg_color=self.colors["success"],
            hover_color="#2DB84C",
            text_color="white",
            corner_radius=4,
            font=("Microsoft YaHei", 10, "bold")
        )
        self.download_selected_btn.pack(side="right", padx=12)

        # 章节列表容器 - 简洁卡片
        list_container = ctk.CTkFrame(
            self.content_frame,
            corner_radius=8,
            fg_color=self.colors["bg_secondary"],
            border_width=1,
            border_color=self.colors["border"]
        )
        list_container.pack(fill="both", expand=True, padx=15, pady=(0, 12))

        # 表头
        header_frame = ctk.CTkFrame(list_container, fg_color="transparent", height=40)
        header_frame.pack(fill="x", padx=12, pady=(10, 0))

        ctk.CTkLabel(
            header_frame,
            text="章节",
            font=("Microsoft YaHei", 10, "bold"),
            width=340,
            anchor="w",
            text_color=self.colors["text_secondary"]
        ).pack(side="left")

        ctk.CTkLabel(
            header_frame,
            text="进度",
            font=("Microsoft YaHei", 10, "bold"),
            width=160,
            text_color=self.colors["text_secondary"]
        ).pack(side="left")

        ctk.CTkLabel(
            header_frame,
            text="状态",
            font=("Microsoft YaHei", 10, "bold"),
            width=80,
            text_color=self.colors["text_secondary"]
        ).pack(side="left")

        ctk.CTkLabel(
            header_frame,
            text="保存位置",
            font=("Microsoft YaHei", 10, "bold"),
            width=280,
            text_color=self.colors["text_secondary"]
        ).pack(side="left")

        # 分隔线
        ctk.CTkFrame(
            list_container,
            height=1,
            fg_color=self.colors["border"]
        ).pack(fill="x", padx=12, pady=8)

        # 可滚动区域
        self.chapter_scroll = ctk.CTkScrollableFrame(
            list_container,
            label_text="",
            fg_color="transparent"
        )
        self.chapter_scroll.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # 加载章节
        self.load_chapters(course)

    def load_chapters(self, course):
        """加载章节列表"""
        x_file_id = course.get("originId")
        dir_id = course.get("xFile", {}).get("dirId")

        if not x_file_id or not dir_id:
            ctk.CTkLabel(
                self.chapter_scroll,
                text="课程信息不完整",
                font=("Microsoft YaHei", 12),
                text_color=self.colors["error"]
            ).pack(pady=20)
            return

        # 显示加载中
        self.load_label = ctk.CTkLabel(
            self.chapter_scroll,
            text="加载中...",
            font=("Microsoft YaHei", 12),
            text_color=self.colors["text_secondary"]
        )
        self.load_label.pack(pady=20)

        def fetch_tasks():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            tasks = loop.run_until_complete(
                self.client.get_task_list(x_file_id, dir_id)
            )
            loop.close()

            self.root.after(0, lambda: self.display_chapters(tasks))

        thread = threading.Thread(target=fetch_tasks, daemon=True)
        thread.start()

    def display_chapters(self, tasks):
        """显示章节列表"""
        if hasattr(self, 'load_label'):
            self.load_label.destroy()

        self.course_cards = []
        self.chapter_tasks = tasks

        if not tasks:
            ctk.CTkLabel(
                self.chapter_scroll,
                text="暂无章节",
                font=("Microsoft YaHei", 12),
                text_color=self.colors["text_secondary"]
            ).pack(pady=20)
            return

        default_path = Path(self.config.settings.get("download_path", "./downloads"))
        course_path = default_path / safe_filename(self.current_course.get("title", "课程"))

        for i, task in enumerate(tasks):
            card = ModernCourseCard(
                self.chapter_scroll,
                task,
                i,
                self.on_chapter_check_changed,
                None,
                course_path,
                self.colors
            )
            self.course_cards.append(card)

    def on_chapter_check_changed(self):
        """章节勾选变化"""
        count = 0
        for card in self.course_cards:
            if card.is_checked():
                count += 1
        self.selected_count.configure(text=f"已选择 {count} 个")

    def select_all_chapters(self):
        """全选"""
        for card in self.course_cards:
            card.set_checked(True)
        self.on_chapter_check_changed()

    def deselect_all_chapters(self):
        """取消全选"""
        for card in self.course_cards:
            card.set_checked(False)
        self.on_chapter_check_changed()

    def update_menu_state(self, active_index):
        """更新菜单按钮状态"""
        for i, btn in enumerate(self.menu_buttons):
            if i == active_index:
                btn.configure(
                    fg_color=self.colors["accent_light"],
                    text_color=self.colors["accent"]
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=self.colors["text_primary"]
                )

    def show_downloads(self):
        """显示下载管理页面"""
        self.current_page = "downloads"
        self.page_title.configure(text="下载管理")

        # 更新菜单按钮状态
        self.update_menu_state(1)

        for widget in self.content_frame.winfo_children():
            widget.destroy()

        # 下载管理容器
        container = ctk.CTkFrame(
            self.content_frame,
            corner_radius=8,
            fg_color=self.colors["bg_secondary"],
            border_width=1,
            border_color=self.colors["border"]
        )
        container.pack(fill="both", expand=True, padx=15, pady=12)

        ctk.CTkLabel(
            container,
            text="📥",
            font=("Microsoft YaHei", 48)
        ).pack(pady=(50, 15))

        ctk.CTkLabel(
            container,
            text="暂无下载任务",
            font=("Microsoft YaHei", 14),
            text_color=self.colors["text_secondary"]
        ).pack()

        ctk.CTkLabel(
            container,
            text="选择课程章节后点击下载开始",
            font=("Microsoft YaHei", 10),
            text_color=self.colors["text_disabled"]
        ).pack(pady=(5, 30))

    def show_history(self):
        """显示下载历史页面"""
        self.current_page = "history"
        self.page_title.configure(text="下载历史")

        # 更新菜单按钮状态
        self.update_menu_state(2)

        for widget in self.content_frame.winfo_children():
            widget.destroy()

        # 历史记录容器
        history_container = ctk.CTkFrame(
            self.content_frame,
            corner_radius=8,
            fg_color=self.colors["bg_secondary"],
            border_width=1,
            border_color=self.colors["border"]
        )
        history_container.pack(fill="both", expand=True, padx=15, pady=12)

        # 表头
        header_frame = ctk.CTkFrame(history_container, fg_color="transparent", height=40)
        header_frame.pack(fill="x", padx=12, pady=(12, 0))

        ctk.CTkLabel(
            header_frame,
            text="文件",
            font=("Microsoft YaHei", 10, "bold"),
            width=380,
            anchor="w",
            text_color=self.colors["text_secondary"]
        ).pack(side="left")

        ctk.CTkLabel(
            header_frame,
            text="时间",
            font=("Microsoft YaHei", 10, "bold"),
            width=130,
            text_color=self.colors["text_secondary"]
        ).pack(side="left")

        ctk.CTkLabel(
            header_frame,
            text="大小",
            font=("Microsoft YaHei", 10, "bold"),
            width=80,
            text_color=self.colors["text_secondary"]
        ).pack(side="left")

        ctk.CTkLabel(
            header_frame,
            text="操作",
            font=("Microsoft YaHei", 10, "bold"),
            width=100,
            text_color=self.colors["text_secondary"]
        ).pack(side="left")

        # 分隔线
        ctk.CTkFrame(
            history_container,
            height=1,
            fg_color=self.colors["border"]
        ).pack(fill="x", padx=12, pady=8)

        # 可滚动区域
        history_scroll = ctk.CTkScrollableFrame(
            history_container,
            label_text="",
            fg_color="transparent"
        )
        history_scroll.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        if not self.config.history:
            ctk.CTkLabel(
                history_scroll,
                text="暂无下载记录",
                font=("Microsoft YaHei", 12),
                text_color=self.colors["text_secondary"]
            ).pack(pady=30)
            return

        # 历史记录列表
        for item in self.config.history[:50]:
            card = ctk.CTkFrame(history_scroll, fg_color="transparent", corner_radius=4)
            card.pack(fill="x", padx=5, pady=2)

            title = item.get("title", "未知文件")
            date = item.get("date", "")
            size = item.get("size", "")
            path = item.get("path", "")

            # 文件名
            ctk.CTkLabel(
                card,
                text=title[:35] + ("..." if len(title) > 35 else ""),
                font=("Microsoft YaHei", 10),
                width=380,
                anchor="w",
                text_color=self.colors["text_primary"]
            ).pack(side="left", padx=8)

            # 时间
            ctk.CTkLabel(
                card,
                text=date,
                font=("Microsoft YaHei", 9),
                width=130,
                text_color=self.colors["text_secondary"]
            ).pack(side="left")

            # 大小
            ctk.CTkLabel(
                card,
                text=size,
                font=("Microsoft YaHei", 9),
                width=80,
                text_color=self.colors["text_secondary"]
            ).pack(side="left")

            # 打开按钮
            ctk.CTkButton(
                card,
                text="打开",
                width=70,
                height=24,
                command=lambda p=path: self.open_folder(p),
                fg_color=self.colors["bg_tertiary"],
                hover_color=self.colors["accent_light"],
                text_color=self.colors["text_primary"],
                corner_radius=4,
                font=("Microsoft YaHei", 9)
            ).pack(side="left", padx=8)

    def show_settings(self):
        """显示设置页面"""
        self.current_page = "settings"
        self.page_title.configure(text="系统设置")

        # 更新菜单按钮状态
        self.update_menu_state(3)

        for widget in self.content_frame.winfo_children():
            widget.destroy()

        # 设置容器
        settings_scroll = ctk.CTkScrollableFrame(
            self.content_frame,
            label_text="",
            fg_color=self.colors["bg_secondary"],
            corner_radius=8,
            border_width=1,
            border_color=self.colors["border"]
        )
        settings_scroll.pack(fill="both", expand=True, padx=15, pady=12)

        # 下载路径设置
        path_frame = ctk.CTkFrame(settings_scroll, fg_color="transparent")
        path_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            path_frame,
            text="下载路径",
            font=("Microsoft YaHei", 12, "bold"),
            anchor="w"
        ).pack(anchor="w", padx=10, pady=(10, 5))

        self.download_path_var = ctk.StringVar(
            value=self.config.settings.get("download_path", "./downloads")
        )
        path_entry = ctk.CTkEntry(
            path_frame,
            textvariable=self.download_path_var,
            font=("Consolas", 10),
            fg_color=self.colors["bg_tertiary"],
            text_color=self.colors["text_primary"],
            border_color=self.colors["border"],
            corner_radius=4
        )
        path_entry.pack(fill="x", padx=10, pady=5)

        ctk.CTkButton(
            path_frame,
            text="选择文件夹",
            width=100,
            height=28,
            command=self.browse_download_path,
            fg_color=self.colors["bg_tertiary"],
            hover_color=self.colors["accent_light"],
            text_color=self.colors["text_primary"],
            corner_radius=4,
            font=("Microsoft YaHei", 10)
        ).pack(anchor="e", padx=10, pady=(0, 10))

        # FFmpeg 路径设置
        ffmpeg_frame = ctk.CTkFrame(settings_scroll, fg_color="transparent")
        ffmpeg_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(
            ffmpeg_frame,
            text="FFmpeg 路径",
            font=("Microsoft YaHei", 12, "bold"),
            anchor="w"
        ).pack(anchor="w", padx=10, pady=(10, 5))

        self.ffmpeg_path_var = ctk.StringVar(
            value=self.config.settings.get("ffmpeg_path", "")
        )
        ffmpeg_entry = ctk.CTkEntry(
            ffmpeg_frame,
            textvariable=self.ffmpeg_path_var,
            font=("Consolas", 10),
            fg_color=self.colors["bg_tertiary"],
            text_color=self.colors["text_primary"],
            border_color=self.colors["border"],
            corner_radius=4
        )
        ffmpeg_entry.pack(fill="x", padx=10, pady=5)

        ctk.CTkButton(
            ffmpeg_frame,
            text="选择 ffmpeg.exe",
            width=120,
            height=28,
            command=self.browse_ffmpeg_path,
            fg_color=self.colors["bg_tertiary"],
            hover_color=self.colors["accent_light"],
            text_color=self.colors["text_primary"],
            corner_radius=4,
            font=("Microsoft YaHei", 10)
        ).pack(anchor="e", padx=10, pady=(0, 10))

        # FFmpeg 状态
        self.ffmpeg_status_detail = ctk.CTkLabel(
            ffmpeg_frame,
            text="",
            font=("Microsoft YaHei", 9),
            text_color=self.colors["text_disabled"],
            anchor="w"
        )
        self.ffmpeg_status_detail.pack(anchor="w", padx=10, pady=5)

        # 主题设置
        theme_frame = ctk.CTkFrame(settings_scroll, fg_color="transparent")
        theme_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(
            theme_frame,
            text="界面主题",
            font=("Microsoft YaHei", 12, "bold"),
            anchor="w"
        ).pack(anchor="w", padx=10, pady=(10, 5))

        theme_options = ["light", "dark"]
        current_theme = self.config.settings.get("theme", "light")

        self.theme_var = ctk.StringVar(value=current_theme)
        theme_menu = ctk.CTkOptionMenu(
            theme_frame,
            values=theme_options,
            variable=self.theme_var,
            command=self.change_theme,
            fg_color=self.colors["bg_tertiary"],
            button_color=self.colors["bg_tertiary"],
            button_hover_color=self.colors["accent_light"],
            dropdown_fg_color=self.colors["bg_secondary"],
            font=("Microsoft YaHei", 10)
        )
        theme_menu.pack(anchor="w", padx=10, pady=5)

        # 保存按钮
        ctk.CTkButton(
            settings_scroll,
            text="保存设置",
            width=120,
            height=36,
            command=self.save_settings,
            fg_color=self.colors["success"],
            hover_color="#2DB84C",
            text_color="white",
            corner_radius=6,
            font=("Microsoft YaHei", 11, "bold")
        ).pack(pady=20)

    def browse_download_path(self):
        """浏览选择下载路径"""
        folder = filedialog.askdirectory(title="选择默认下载位置")
        if folder:
            self.download_path_var.set(folder)

    def browse_ffmpeg_path(self):
        """浏览选择 FFmpeg 路径"""
        file = filedialog.askopenfilename(
            title="选择 ffmpeg.exe",
            filetypes=[("可执行文件", "*.exe"), ("所有文件", "*.*")]
        )
        if file and file.endswith('ffmpeg.exe'):
            self.ffmpeg_path_var.set(file)
            self.check_ffmpeg_path(file)

    def check_ffmpeg_path(self, path):
        """检查指定路径的 FFmpeg"""
        try:
            result = subprocess.run(
                [path, "-version"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                version = result.stdout.split('\n')[0][:40]
                self.ffmpeg_status_detail.configure(
                    text=f"已检测: {version}",
                    text_color=self.colors["success"]
                )
                return True
        except:
            pass

        self.ffmpeg_status_detail.configure(
            text="未检测到有效的 FFmpeg",
            text_color=self.colors["error"]
        )
        return False

    def change_theme(self, theme):
        """切换主题"""
        self.theme_name = theme
        self.colors = ThemeManager.get_colors(theme)
        ctk.set_appearance_mode(theme)
        self.config.save_settings({"theme": theme})

    def save_settings(self):
        """保存设置"""
        settings = {
            "download_path": self.download_path_var.get(),
            "ffmpeg_path": self.ffmpeg_path_var.get(),
            "theme": self.theme_var.get()
        }
        self.config.save_settings(settings)

        # 更新下载器配置
        self.download_manager.ffmpeg_path = self.ffmpeg_path_var.get()

        messagebox.showinfo("成功", "设置已保存")

    # ============== 登录相关 ==============

    def try_auto_login(self):
        """尝试自动登录"""
        token_data = self.config.token
        if token_data and token_data.get("access_token"):
            self.client = PlasoAPIClient(token_data["access_token"])

            # 验证 token
            result = self.client.validate_token()
            if result["success"]:
                self.update_login_state(True, token_data)
            else:
                self.update_login_state(False)

    def update_login_state(self, logged_in: bool, token_data: dict = None):
        """更新登录状态 UI"""
        if logged_in and token_data:
            name = token_data.get("user_info", {}).get("name", "用户")
            org_name = token_data.get("user_info", {}).get("myOrg", {}).get("name", "")

            self.user_info_label.configure(
                text=f"登录: {name}\n{org_name}" if org_name else f"登录: {name}",
                text_color=self.colors["success"]
            )
            self.token_entry.pack_forget()
            self.login_btn.pack_forget()
            self.logout_btn.pack(fill="x", pady=5)
        else:
            self.user_info_label.configure(text="")
            self.logout_btn.pack_forget()
            self.token_entry.pack(fill="x", pady=(0, 5))
            self.login_btn.pack(fill="x")

    def logout(self):
        """退出登录"""
        self.config.clear_token()
        self.client = None
        self.courses = []
        self.update_login_state(False)

        if self.current_page == "courses":
            self.show_courses()

        messagebox.showinfo("提示", "已退出登录")

    # ============== 下载相关 ==============

    def refresh_courses(self):
        """刷新课程列表"""
        if not self.client:
            messagebox.showwarning("警告", "请先登录！")
            return

        if self.current_page == "courses":
            self.show_courses()
            # 重新加载
            self.load_label = ctk.CTkLabel(
                self.course_scroll,
                text="加载中...",
                font=("Microsoft YaHei", 12),
                text_color=self.colors["text_secondary"]
            )
            self.load_label.pack(pady=20)

            def fetch():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                courses = loop.run_until_complete(self.client.get_course_list())
                loop.close()
                self.courses = courses
                self.root.after(0, self.display_courses)

            thread = threading.Thread(target=fetch, daemon=True)
            thread.start()

    def check_ffmpeg_status(self):
        """检查 FFmpeg 状态"""
        self.download_manager.find_ffmpeg()

        if self.download_manager.ffmpeg_path:
            try:
                result = subprocess.run(
                    [self.download_manager.ffmpeg_path, "-version"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    version = result.stdout.split('\n')[0][:25]
                    self.ffmpeg_status.configure(
                        text=f"FFmpeg: {version}...",
                        text_color=self.colors["success"]
                    )
                    return
            except:
                pass

        self.ffmpeg_status.configure(
            text="FFmpeg: 未检测",
            text_color=self.colors["error"]
        )

    def start_batch_download(self):
        """批量下载"""
        selected_tasks = []

        for card in self.course_cards:
            if card.is_checked():
                selected_tasks.append({
                    "task_data": card.card_frame.task_data,
                    "save_path": card.path_var.get(),
                    "card": card
                })

        if not selected_tasks:
            messagebox.showwarning("警告", "请先选择要下载的章节！")
            return

        if self.downloading:
            messagebox.showinfo("提示", "下载任务正在进行中...")
            return

        # 检查 FFmpeg
        if not self.download_manager.ffmpeg_path:
            messagebox.showerror("错误", "未检测到 FFmpeg，请先在设置中配置 FFmpeg 路径！")
            self.show_settings()
            return

        self.downloading = True
        self.download_tasks = selected_tasks
        self.completed_count = 0
        self.failed_count = 0

        # 禁用按钮
        self.download_selected_btn.configure(state="disabled", text="下载中...", fg_color=self.colors["text_disabled"])

        def download_worker():
            total = len(self.download_tasks)

            for task in self.download_tasks:
                if not self.downloading:
                    break

                task_data = task["task_data"]
                save_path = task["save_path"]
                card = task["card"]

                # 更新状态
                self.root.after(0, lambda c=card: c.update_status("解析中...", self.colors["warning"]))

                record_files = task_data.get("recordFiles", [])
                if not record_files:
                    self.root.after(0, lambda c=card: c.update_status("无视频", self.colors["error"]))
                    self.root.after(0, lambda: c.card_frame.progress.set(0))
                    self.failed_count += 1
                    continue

                record_file = record_files[0]
                location_path = record_file.get("location") or record_file.get("locationPath")

                if not location_path:
                    self.root.after(0, lambda c=card: c.update_status("无地址", self.colors["error"]))
                    self.root.after(0, lambda: c.card_frame.progress.set(0))
                    self.failed_count += 1
                    continue

                m3u8_url = f"https://filecdn.plaso.com/liveclass/plaso/{location_path}/a1/a.m3u8"

                # 下载
                def progress_callback(value):
                    self.root.after(0, lambda v=value, c=card: c.set_progress(v))

                def finished_callback(success, message):
                    if success:
                        self.root.after(0, lambda c=card, m=message: c.update_status(m, self.colors["success"]))
                        self.completed_count += 1

                        # 添加历史记录
                        self.config.add_history({
                            "title": task_data.get("name", "未知"),
                            "path": save_path,
                            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "size": message
                        })
                    else:
                        self.root.after(0, lambda c=card: c.update_status("失败", self.colors["error"]))
                        self.failed_count += 1

                    # 更新总进度
                    current = self.completed_count + self.failed_count
                    self.root.after(0, lambda: self.selected_count.configure(
                        text=f"下载中 {current}/{total}"
                    ))

                self.download_manager.download_video(
                    m3u8_url,
                    save_path,
                    progress_callback,
                    finished_callback
                )

            self.root.after(0, self.batch_download_finished)

        thread = threading.Thread(target=download_worker, daemon=True)
        thread.start()

    def batch_download_finished(self):
        """批量下载完成"""
        self.downloading = False
        self.download_selected_btn.configure(
            state="normal",
            text="下载选中",
            fg_color=self.colors["success"]
        )

        total = len(self.download_tasks)
        messagebox.showinfo(
            "下载完成",
            f"成功: {self.completed_count}\n失败: {self.failed_count}\n总计: {total}"
        )

        self.selected_count.configure(text="已选择 0 个")

    def open_folder(self, path):
        """打开文件夹"""
        try:
            folder = str(Path(path).parent)
            if os.name == 'nt':
                os.startfile(folder)
            elif sys.platform == 'darwin':
                subprocess.run(['open', folder])
            else:
                subprocess.run(['xdg-open', folder])
        except Exception as e:
            print(f"打开文件夹失败: {e}")

    # ============== 经典 UI 回退 ==============

    def setup_classic_ui(self):
        """设置经典 UI（当 CustomTkinter 不可用时）"""
        self.root = tk.Tk()
        self.root.title("伯索云课堂课程下载器")
        self.root.geometry("1100x700")

        # 简化版 UI
        tk.Label(
            self.root,
            text="请安装 CustomTkinter 以获得更好的体验:\n\npip install customtkinter",
            font=("Microsoft YaHei", 14),
            fg="red"
        ).pack(pady=100)

        tk.Button(self.root, text="退出", command=self.root.quit).pack()


# ============== 主程序入口 ==============

def main():
    """主函数"""
    app = BersoDownloaderApp()
    app.root.mainloop()


if __name__ == "__main__":
    main()
