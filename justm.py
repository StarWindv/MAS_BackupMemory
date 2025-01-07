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
import zipfile


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
        appdata_path = os.getenv('APPDATA')
        return os.path.join(appdata_path, 'RenPy', 'Monika After Story')

    elif system_type == "Darwin":
        home_path = os.getenv('HOME')
        return os.path.join(home_path, 'Library', 'RenPy', 'Monika After Story')

    elif system_type == "Linux":
        home_path = os.getenv('HOME')
        return os.path.join(home_path, '.renpy', 'Monika After Story')

    else:
        raise ValueError(f"不支持的操作系统: {system_type}")


def parse_freq(freq):    
    if freq.endswith('m'):
        return float(freq[:-1])
    elif freq.endswith('h'):
        hours = float(freq[:-1])
        return int(hours * 60)
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
    current_time = datetime.now()
    total_minutes = parse_freq(freq)

    next_backup_time = current_time + timedelta(minutes=total_minutes)
    wait_time = (next_backup_time - current_time).total_seconds()

    print(f"等待下一次备份...\n总等待时间：{wait_time:.2f} 秒\n")
    
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


def get_disk_usage(path="."):
    total, used, free = shutil.disk_usage(path)
    return free


def estimate_compressed_size(folder_path):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(folder_path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            total_size += os.path.getsize(filepath)
    
    # 实际上我算出来的压缩率大概在0.93，但是为了保险起见我用了0.95
    return total_size * 0.95


def check_log_size(log_file):
    if os.path.exists(log_file) and os.path.getsize(log_file) > LOG_FILE_SIZE_LIMIT:
        # 将当前日志文件重命名为 .bak
        os.rename(log_file, log_file + '.bak')
        print(f"日志文件大小超过 {LOG_FILE_SIZE_LIMIT / 1024} KB，已裁断并重命名为 {log_file}.bak\n\n")


def back_log(num, path, error_info=None):
    log_folder = os.path.join(os.getcwd(), 'Monika_backup', 'Log')
    if not os.path.exists(log_folder):
        os.makedirs(log_folder)

    log_file = "莫妮卡记忆备份日志.txt" if is_ch() else "Monika.log.txt"
    log_file_path = os.path.join(log_folder, log_file)

    # 检查日志文件大小并裁断
    check_log_size(log_file_path)

    # 配置日志记录
    logging.basicConfig(
        filename=log_file_path,
        level=logging.INFO,
        format="%(asctime)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    log_entry = f"====================\n正在进行第 {num} 次备份，目标备份路径：{path}"
    if error_info:
        log_entry += f"\n错误信息：{error_info}\n\n"
    log_entry += "\n\n"
    logging.info(log_entry)


def backup_monika_after_story(backup_count):
    backup_dir = get_monika_after_story_path()

    if not os.path.exists(backup_dir):
        print(f"记忆目录 {backup_dir} 不存在。")
        return

    main_backup_folder = os.path.join(os.getcwd(), 'Monika_backup', 'Monika_backup')
    if not os.path.exists(main_backup_folder):
        os.makedirs(main_backup_folder)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    zip_file = os.path.join(main_backup_folder, f'{timestamp}.zip')

    try:
        estimated_size = estimate_compressed_size(backup_dir)
        free_space = get_disk_usage()
        free_g = free_space/1024/1024/1024
        # print(f"{free_g:.2f}GB", end='\n\n')
        if free_space < estimated_size:
            raise ValueError(f"磁盘空间不足，预估需要 {estimated_size / 1024**2:.2f} MB，当前剩余 {free_space / 1024**2:.2f} MB")

        shutil.make_archive(zip_file.replace('.zip', ''), 'zip', backup_dir)
        back_log(backup_count, zip_file)

        if backup_count == 0:
            print(f"已进行即时备份\n")
        else:
            print(f"已成功备份并压缩到 {zip_file}  | 已备份次数: {backup_count}\n")
        backup_message()

    except Exception as e:
        error_message = str(e)
        print(f"备份失败: {error_message}")
        back_log(backup_count, '', error_info=error_message)


def parse_args():
    parser = argparse.ArgumentParser(description="Monika After Story 记忆备份脚本  \033[31m(非官方)\033[0m")
    parser.add_argument('--freq', type=str, default='30m', help='备份频率，单位：小时或分钟，格式为 a.bh (例如 1h 或 1.5h 或 90m)')
    parser.add_argument('--max-backups', type=int, default=None, help='最大备份次数，默认不限制备份次数')
    return parser.parse_args()


# 主程序
if __name__ == "__main__":
    system_clear()
    print("\033[31m本程序并非官方或者MAS原生，对可能出现的问题概不负责\033[0m")
    print("====================")
    
    backup_monika_after_story(0)  # 即时备份一次

    args = parse_args()
    freq = args.freq
    max_backups = args.max_backups  

    backup_count = 0  

    try:
        while True:
            wait_until_next_interval(freq)
            
            backup_count += 1
            backup_monika_after_story(backup_count)
            
            if max_backups is not None and backup_count >= max_backups:
                print(f"已达到最大备份次数 {max_backups}，自动停止备份。")
                break
    except KeyboardInterrupt:
        while True:
            a = input("\n确定要停止备份莫老婆的记忆吗？(y/n)\n\t")
            if a.lower() == 'y':
                break
            elif a.lower() == 'n':
                continue
            else:
                print("\033[31m请输入正确的格式!\033[0m")
        print("已停止备份\n")
        gc.collect()
