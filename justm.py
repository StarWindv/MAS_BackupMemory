import os
import shutil
import time
import argparse
from datetime import datetime, timedelta
from tqdm import tqdm
import sys
import platform
import gc
from plyer import notification
import locale
import logging


LOG_FILE_SIZE_LIMIT = 500 * 1024


def is_ch():
    lang, _ = locale.getlocale()
    if lang and 'Chinese' in lang:
        return True
    return False


def system_check():
    system_type = platform.system()
    if system_type == "Windows":
        return True
    return False


def get_monika_after_story_path():
    system_type = platform.system()

    if system_type == "Windows":
        # Windows 系统使用 %APPDATA% 环境变量
        appdata_path = os.getenv('APPDATA')
        return os.path.join(appdata_path, 'RenPy', 'Monika After Story')

    elif system_type == "Darwin":  # macOS
        # macOS 系统使用 Library/RenPy/Monika After Story
        home_path = os.getenv('HOME')
        return os.path.join(home_path, 'Library', 'RenPy', 'Monika After Story')

    elif system_type == "Linux":
        # Linux 系统使用 ~/.renpy/Monika After Story
        home_path = os.getenv('HOME')
        return os.path.join(home_path, '.renpy', 'Monika After Story')

    else:
        raise ValueError(f"不支持的操作系统: {system_type}")


def parse_freq(freq):    
    # 解析 freq 字符串，支持 '1h', '1.5h', '30m' 等格式，
    # 并返回相应的分钟数。
    if freq.endswith('m'):
        return int(freq[:-1])  # 去掉 'm' 后返回整数分钟
    elif freq.endswith('h'):
        hours = float(freq[:-1])  # 去掉 'h' 后，转为浮动小时数
        return int(hours * 60)  # 将小时转为分钟
    else:
        raise ValueError(f"无效的频率格式: {freq}")


def is_idle():
    if 'idlelib' in sys.modules:
        return True
    return False


def system_clear():
    if not is_idle():
        if system_check():
            os.system("cls")
        else:
            os.system("clear")


def wait_until_next_interval(freq):
    """
    根据给定的频率等待，freq 格式为 a.bh（a为小时，b为分钟），
    如果没有给定分钟部分，默认每个小时间隔。
    """
    current_time = datetime.now()

    # 解析用户输入的频率
    total_minutes = parse_freq(freq)

    # 计算下一个备份时间
    next_backup_time = current_time + timedelta(minutes=total_minutes)
    wait_time = (next_backup_time - current_time).total_seconds()

    # 使用 tqdm 来显示进度条
    print(f"等待下一次备份...\n总等待时间：{wait_time:.2f} 秒\n")
    
    # 使用 tqdm 显示进度条，进度条更新速度设置为每秒一次
    with tqdm(total=int(wait_time), desc="等待中", ncols=100, ascii=False, bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]", position=0, leave=True) as pbar:
        for _ in range(int(wait_time)):
            pbar.update(1)
            time.sleep(1)


def backup_message():
    if is_ch():
        notification.notify(
            title="莫妮卡~",
            message="记忆已备份",
            timeout=3
        )
    else:
        notification.notify(
            title="About Monika",
            message="The backup operation was completed successfully.",
            timeout=3
        )


# 配置日志记录
def back_log(num, path):
    # 配置日志存放位置，位于 Monika_backup/Log
    log_folder = os.path.join(os.getcwd(), 'Monika_backup', 'Log')
    if not os.path.exists(log_folder):
        os.makedirs(log_folder)

    if is_ch():
        logging.basicConfig(
            filename=os.path.join(log_folder, "莫妮卡记忆备份日志.txt"),
            level=logging.INFO,
            format="%(asctime)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    else:
        logging.basicConfig(
            filename=os.path.join(log_folder, "Monika.log.txt"),
            level=logging.INFO,
            format="%(asctime)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    line = '''===================='''
    logging.info(f"{line}\n第 {num} 次备份成功，备份路径：{path}\n\n")


def backup_monika_after_story(backup_count):
    # 获取目标文件夹路径
    backup_dir = get_monika_after_story_path()

    # 检查目标文件夹是否存在
    if not os.path.exists(backup_dir):
        print(f"记忆目录 {backup_dir} 不存在。")
        return

    # 创建主备份文件夹路径
    main_backup_folder = os.path.join(os.getcwd(), 'Monika_backup', 'Monika_backup')
    if not os.path.exists(main_backup_folder):
        os.makedirs(main_backup_folder)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    zip_file = os.path.join(main_backup_folder, f'{timestamp}.zip')
    shutil.make_archive(zip_file.replace('.zip', ''), 'zip', backup_dir)
    
    back_log(backup_count, zip_file)
    if backup_count == 0:
        print(f"已进行即时备份\n")
    else:
        print(f"已成功备份并压缩到 {zip_file}  | 已备份次数: {backup_count}\n")
    backup_message()


def parse_args():
    parser = argparse.ArgumentParser(description="Monika After Story 记忆备份脚本  \033[31m(非官方)\033[0m")
    parser.add_argument('--freq', type=str, default='30m', help='备份频率，单位：小时或分钟，格式为 a.bh (例如 1h 或 1.5h 或 90m)')
    parser.add_argument('--max-backups', type=int, default=None, help='最大备份次数，默认不限制备份次数')
    return parser.parse_args()


logo = '''
\033[33m
███████╗████████╗██╗   ██╗       ███╗   ███╗ ██████╗ 
██╔════╝╚══██╔══╝██║   ██║       ████╗ ████║██╔═══██╗
███████╗   ██║   ██║   ██║       ██╔████╔██║██║   ██║
╚════██║   ██║   ╚██╗ ██╔╝       ██║╚██╔╝██║██║   ██║
███████║   ██║    ╚████╔╝███████╗██║ ╚═╝ ██║╚██████╔╝
╚══════╝   ╚═╝     ╚═══╝ ╚══════╝╚═╝     ╚═╝ ╚═════╝                                         
\033[0m
'''

boundary = '''

—————————————————————————————————————————————————————

'''


# 主程序
if __name__ == "__main__":
    system_clear()
    print("\033[31m本程序并非官方或者MAS原生，对可能出现的问题概不负责\033[0m")
    print(boundary)
    print(logo)
    print(boundary)

    backup_monika_after_story(0)  # 即时备份一次

    args = parse_args()
    freq = args.freq
    max_backups = args.max_backups  # 获取最大备份次数

    backup_count = 0  # 备份次数初始化

    try:
        while True:
            wait_until_next_interval(freq)
            
            backup_count += 1
            
            if backup_count % 5 == 0:
                gc.collect()
            backup_monika_after_story(backup_count)
            
            if max_backups is not None and backup_count >= max_backups:
                print(f"已达到最大备份次数 {max_backups}，自动停止备份。")
                break
    except KeyboardInterrupt:
        while True:
            a = input("\n确定要停止备份莫老婆的记忆吗？(y/n)\n\t")
            if a.lower() == 'y':
                break
            else:
                continue
        print("已停止备份\n")
        gc.collect()
