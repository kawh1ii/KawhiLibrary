import os
import re
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import subprocess
import threading
from urllib.parse import urlparse
import json
import sys
import traceback

# 设置默认编码为 UTF-8
if sys.platform == 'win32':
    # Windows 系统设置
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    # 设置控制台代码页为 UTF-8
    try:
        import ctypes

        ctypes.windll.kernel32.SetConsoleCP(65001)
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
    except:
        pass


class VideoDownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("视频下载器")
        self.root.geometry("800x600")
        self.root.minsize(600, 400)

        # 设置样式
        self.style = ttk.Style()
        self.style.configure('TButton', padding=6)
        self.style.configure('Header.TLabel', font=('Arial', 12, 'bold'))

        self.yt_dlp_cmd = 'yt-dlp'
        self.downloading = False
        self.current_process = None
        self.aria2c_available = False

        self.create_widgets()
        self.check_dependencies()

    def create_widgets(self):
        """创建界面组件"""
        # 主容器
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # 标题
        title_label = ttk.Label(main_frame, text="视频下载器", style='Header.TLabel')
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 10))

        # URL输入区域
        url_frame = ttk.LabelFrame(main_frame, text="视频URL", padding=10)
        url_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)

        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(url_frame, textvariable=self.url_var, width=50)
        self.url_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        url_frame.columnconfigure(0, weight=1)

        # 获取信息按钮
        self.info_btn = ttk.Button(url_frame, text="获取信息", command=self.get_video_info)
        self.info_btn.grid(row=0, column=1)

        # 视频信息显示区域
        info_frame = ttk.LabelFrame(main_frame, text="视频信息", padding=10)
        info_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)

        self.info_text = tk.Text(info_frame, height=4, width=50)
        self.info_text.grid(row=0, column=0, sticky=(tk.W, tk.E))
        info_frame.columnconfigure(0, weight=1)

        # 下载选项区域
        options_frame = ttk.LabelFrame(main_frame, text="下载选项", padding=10)
        options_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)

        # 下载类型
        ttk.Label(options_frame, text="下载类型:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.download_type = tk.StringVar(value="video")
        ttk.Radiobutton(options_frame, text="视频", variable=self.download_type,
                        value="video").grid(row=0, column=1, padx=5)
        ttk.Radiobutton(options_frame, text="仅音频", variable=self.download_type,
                        value="audio").grid(row=0, column=2, padx=5)

        # 视频质量
        ttk.Label(options_frame, text="视频质量:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.quality_var = tk.StringVar(value="best")
        self.quality_combo = ttk.Combobox(options_frame, textvariable=self.quality_var,
                                          values=["best", "1080p", "720p", "480p", "360p"],
                                          state="readonly", width=10)
        self.quality_combo.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

        # 加速下载选项
        ttk.Label(options_frame, text="加速下载:").grid(row=1, column=2, padx=5, pady=5, sticky=tk.W)
        self.turbo_var = tk.BooleanVar(value=True)
        self.turbo_check = ttk.Checkbutton(options_frame, text="启用多线程加速",
                                           variable=self.turbo_var)
        self.turbo_check.grid(row=1, column=3, padx=5, pady=5, sticky=tk.W)

        # 保存路径
        ttk.Label(options_frame, text="保存路径:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)

        path_frame = ttk.Frame(options_frame)
        path_frame.grid(row=2, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        self.path_var = tk.StringVar(value=os.path.expanduser("~/Downloads"))
        self.path_entry = ttk.Entry(path_frame, textvariable=self.path_var, width=40)
        self.path_entry.grid(row=0, column=0, padx=(0, 5))

        self.browse_btn = ttk.Button(path_frame, text="浏览", command=self.browse_path)
        self.browse_btn.grid(row=0, column=1)

        # 下载按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=3, pady=20)

        self.download_btn = ttk.Button(button_frame, text="开始下载",
                                       command=self.start_download, style='Accent.TButton')
        self.download_btn.grid(row=0, column=0, padx=5)

        self.cancel_btn = ttk.Button(button_frame, text="取消下载",
                                     command=self.cancel_download, state=tk.DISABLED)
        self.cancel_btn.grid(row=0, column=1, padx=5)

        # 进度条
        progress_frame = ttk.LabelFrame(main_frame, text="下载进度", padding=10)
        progress_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var,
                                            maximum=100, length=400)
        self.progress_bar.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        progress_frame.columnconfigure(0, weight=1)

        self.progress_label = ttk.Label(progress_frame, text="等待下载...")
        self.progress_label.grid(row=1, column=0, columnspan=2, pady=5)

        # 日志区域
        log_frame = ttk.LabelFrame(main_frame, text="日志", padding=10)
        log_frame.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)

        self.log_text = tk.Text(log_frame, height=8, width=50)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 滚动条
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.log_text.configure(yscrollcommand=scrollbar.set)

        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        # 提示信息
        tip_frame = ttk.Frame(main_frame)
        tip_frame.grid(row=7, column=0, columnspan=3, pady=5)

        tip_label = ttk.Label(tip_frame, text="提示：如需更快下载速度，请安装 aria2c 并启用多线程加速选项",
                              foreground="blue")
        tip_label.grid(row=0, column=0)

        # 设置主框架的权重
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(6, weight=1)

    def log(self, message):
        """添加日志"""
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.root.update()

    def check_dependencies(self):
        """检查依赖"""
        missing_deps = []

        # 检查 yt-dlp
        yt_dlp_found = False
        for cmd in ['yt-dlp', 'yt-dlp.exe']:
            try:
                subprocess.run([cmd, '--version'], capture_output=True, check=True,
                               encoding='utf-8', errors='replace')
                self.yt_dlp_cmd = cmd
                yt_dlp_found = True
                break
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue

        if not yt_dlp_found:
            missing_deps.append('yt-dlp')

        # 检查 ffmpeg
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True,
                           encoding='utf-8', errors='replace')
        except (subprocess.CalledProcessError, FileNotFoundError):
            missing_deps.append('ffmpeg')

        # 检查 aria2c (可选，用于加速)
        try:
            subprocess.run(['aria2c', '--version'], capture_output=True, check=True,
                           encoding='utf-8', errors='replace')
            self.aria2c_available = True
            self.log("检测到 aria2c，将使用多线程加速下载")
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.aria2c_available = False
            self.log("未检测到 aria2c，使用默认下载器（可选安装 aria2c 以获得更快速度）")

        if missing_deps:
            message = "缺少以下依赖，请先安装：\n\n"
            for dep in missing_deps:
                if dep == 'yt-dlp':
                    message += f"- {dep}: pip install yt-dlp\n"
                elif dep == 'ffmpeg':
                    message += f"- {dep}: 请从 https://ffmpeg.org/download.html 下载安装\n"

            messagebox.showerror("缺少依赖", message)
            self.download_btn.config(state=tk.DISABLED)
        else:
            self.log("所有必需依赖已就绪")

    def browse_path(self):
        """浏览保存路径"""
        path = filedialog.askdirectory(initialdir=self.path_var.get())
        if path:
            self.path_var.set(path)

    def get_video_info(self):
        """获取视频信息"""
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("警告", "请输入视频URL")
            return

        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(tk.END, "正在获取视频信息...")

        def get_info():
            try:
                cmd = [self.yt_dlp_cmd, '--dump-json', url]
                result = subprocess.run(cmd, capture_output=True, text=True,
                                        encoding='utf-8', errors='replace')

                if result.returncode == 0:
                    info = json.loads(result.stdout)

                    # 更新信息显示
                    self.info_text.delete(1.0, tk.END)
                    info_text = f"标题: {info.get('title', '未知')}\n"
                    info_text += f"时长: {info.get('duration', 0)}秒\n"
                    info_text += f"上传者: {info.get('uploader', '未知')}\n"
                    info_text += f"分辨率: {info.get('resolution', '未知')}"

                    self.info_text.insert(tk.END, info_text)
                else:
                    error_message = result.stderr if result.stderr else "获取信息失败，未知错误"
                    self.info_text.delete(1.0, tk.END)
                    self.info_text.insert(tk.END, f"错误: {error_message}")
                    self.log(f"获取信息失败: {error_message}")
            except json.JSONDecodeError as e:
                error_message = f"JSON解析错误: {str(e)}"
                self.info_text.delete(1.0, tk.END)
                self.info_text.insert(tk.END, error_message)
                self.log(error_message)
            except Exception as e:
                error_message = f"获取信息时出错: {str(e)}\n{traceback.format_exc()}"
                self.info_text.delete(1.0, tk.END)
                self.info_text.insert(tk.END, error_message)
                self.log(error_message)

        threading.Thread(target=get_info, daemon=True).start()

    def parse_progress(self, line):
        """解析进度信息"""
        patterns = {
            'percent': r'(\d+\.?\d*)%',
            'size': r'of\s+([\d\.]+\s*[KMG]i?B)',
            'speed': r'at\s+([\d\.]+\s*[KMG]i?B/s)',
            'eta': r'ETA\s+([\d:]+)'
        }

        result = {}
        for key, pattern in patterns.items():
            match = re.search(pattern, line)
            if match:
                result[key] = match.group(1)

        return result

    def start_download(self):
        """开始下载"""
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("警告", "请输入视频URL")
            return

        # 更新UI状态
        self.downloading = True
        self.download_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.NORMAL)
        self.progress_var.set(0)
        self.progress_label.config(text="准备下载...")

        # 清空日志
        self.log_text.delete(1.0, tk.END)
        self.log("开始下载...")

        # 在新线程中执行下载
        threading.Thread(target=self.download_thread, daemon=True).start()

    def download_thread(self):
        """下载线程"""
        url = self.url_var.get().strip()
        output_path = self.path_var.get()
        quality = self.quality_var.get()
        download_type = self.download_type.get()
        use_turbo = self.turbo_var.get()

        # 确保输出目录存在
        os.makedirs(output_path, exist_ok=True)

        # 构建基础命令
        base_cmd = [
            self.yt_dlp_cmd,
            '--progress',
            '-o', os.path.join(output_path, '%(title)s.%(ext)s'),
        ]

        # 添加加速选项（如果启用）
        if use_turbo:
            turbo_args = [
                '--concurrent-fragments', '16',  # 使用16个并发片段下载
                '--no-check-certificate',  # 跳过证书检查
                '--buffer-size', '16K',  # 设置缓冲区大小
                '--retries', '10',  # 增加重试次数
                '--fragment-retries', '10',  # 片段重试次数
                '--no-part',  # 不使用.part文件
            ]

            # 如果aria2c可用，使用它作为外部下载器
            if self.aria2c_available:
                turbo_args.extend([
                    '--downloader', 'aria2c',
                    '--downloader-args', 'aria2c:"-x 16 -s 16 -k 1M -j 16 --enable-color=false"',
                ])
                self.log("使用 aria2c 多线程加速下载（16线程）")
            else:
                turbo_args.extend([
                    '--external-downloader-args', '-j 16',  # 尝试使用内置多线程
                ])
                self.log("使用内置多线程加速下载")

            base_cmd.extend(turbo_args)
        else:
            self.log("使用标准下载模式")

        # 构建完整命令
        if download_type == "audio":
            cmd = base_cmd + [
                '-f', 'bestaudio/best',
                '-x',
                '--audio-format', 'mp3',
                url
            ]
        else:
            cmd = base_cmd + [
                '-f', quality,
                '--no-playlist',
                '--merge-output-format', 'mp4',
                url
            ]

        try:
            self.log(f"执行命令: {' '.join(cmd)}")

            self.current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                encoding='utf-8',
                errors='replace',  # 处理无法解码的字符
                bufsize=1
            )

            error_output = []
            warning_output = []

            while True:
                if self.current_process is None:
                    break

                output = self.current_process.stdout.readline()
                if output == '' and self.current_process.poll() is not None:
                    break

                if output:
                    line = output.strip()

                    # 收集错误和警告信息
                    if "ERROR:" in line or "错误:" in line:
                        error_output.append(line)
                        self.log(f"错误: {line}")
                    elif "WARNING:" in line or "警告:" in line:
                        warning_output.append(line)
                        self.log(f"警告: {line}")

                    # 解析进度
                    progress_info = self.parse_progress(line)

                    if progress_info.get('percent'):
                        try:
                            percent = float(progress_info['percent'])
                            self.progress_var.set(percent)

                            # 更新进度标签
                            status_parts = []
                            if progress_info.get('size'):
                                status_parts.append(f"大小: {progress_info['size']}")
                            if progress_info.get('speed'):
                                status_parts.append(f"速度: {progress_info['speed']}")
                            if progress_info.get('eta'):
                                status_parts.append(f"剩余: {progress_info['eta']}")

                            status = " | ".join(status_parts)
                            self.progress_label.config(text=f"{percent:.1f}% - {status}")
                        except ValueError:
                            pass

                    # 添加到日志（不是所有行都显示）
                    if line and not line.startswith('[download]'):
                        self.log(line)

            # 检查结果
            returncode = self.current_process.returncode if self.current_process else -1

            if returncode == 0 and not error_output:
                self.progress_var.set(100)
                self.progress_label.config(text="下载完成！")
                self.log("下载成功完成！")
                if warning_output:
                    self.log(f"完成时有{len(warning_output)}个警告")
                messagebox.showinfo("成功", "下载完成！")
            else:
                error_summary = "\n".join(error_output) if error_output else "下载失败，未捕获到具体错误信息"
                self.progress_label.config(text="下载失败")
                self.log(f"下载失败，返回代码: {returncode}")
                self.log(f"错误信息:\n{error_summary}")

                # 显示详细的错误信息
                messagebox.showerror("下载失败", f"下载出错:\n\n{error_summary}")

        except FileNotFoundError as e:
            error_msg = f"找不到程序: {str(e)}\n请确保 yt-dlp 和相关依赖已正确安装"
            self.log(error_msg)
            self.progress_label.config(text="程序未找到")
            messagebox.showerror("程序未找到", error_msg)

        except subprocess.SubprocessError as e:
            error_msg = f"子进程错误: {str(e)}\n{traceback.format_exc()}"
            self.log(error_msg)
            self.progress_label.config(text="子进程错误")
            messagebox.showerror("子进程错误", error_msg)

        except Exception as e:
            error_msg = f"未知错误: {str(e)}\n{traceback.format_exc()}"
            self.log(error_msg)
            self.progress_label.config(text="未知错误")
            messagebox.showerror("未知错误", error_msg)

        finally:
            # 重置UI状态
            self.downloading = False
            self.download_btn.config(state=tk.NORMAL)
            self.cancel_btn.config(state=tk.DISABLED)
            self.current_process = None

    def cancel_download(self):
        """取消下载"""
        if self.current_process:
            self.current_process.terminate()
            self.current_process = None
            self.progress_label.config(text="下载已取消")
            self.log("用户取消了下载")
            messagebox.showinfo("提示", "下载已取消")


def main():
    root = tk.Tk()
    app = VideoDownloaderGUI(root)

    # 使窗口居中
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f"{width}x{height}+{x}+{y}")

    root.mainloop()


if __name__ == "__main__":
    main()