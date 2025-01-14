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

# locale.setlocale(locale.LC_ALL, 'en_US.UTF-8') # 临时设置为非中文以测试对应功能
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
        if is_ch():
            raise ValueError(f"\033[31m不支持的操作系统: {system_type}\033[0m")
        else:
            raise ValueError(f"\033[31mUnsupported operating system:{system_type}\033[0m")


def parse_freq(freq):    
    if freq.endswith('m'):
        return float(freq[:-1])
    elif freq.endswith('h'):
        hours = float(freq[:-1])
        return int(hours * 60)
    else:
        if is_ch():
            raise ValueError(f"\033[31m无效的频率格式: {freq}\033[0m")
        else:
            raise ValueError(f"\033[31mInvalid format for frequency: {freq}\033[0m")


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

    if is_ch():
        print(f"等待下一次备份...\n总等待时间：{wait_time:.2f} 秒\n")
    else:
        print(f" Waiting for the next backup... \n Total wait time: {wait_time:.2f} seconds \n")

    if is_idle():
        time.sleep(wait_time)
    else:
        with tqdm(total=int(wait_time), desc="等待中", ncols=100, ascii=False, bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]", position=0, leave=True) as pbar:
            for _ in range(int(wait_time)):
                pbar.update(1)
                time.sleep(1)
    gc.collect()


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
        if is_ch():
            print(f"日志文件大小超过 {LOG_FILE_SIZE_LIMIT / 1024} KB\n日志已裁断\n过往日志重命名为 {log_file}.bak\n\n")
        else:
            print(f"The log file size exceeds {LOG_FILE_SIZE_LIMIT / 1024} KB\nThe log file has been truncated.\nPast log renamed to {log_file}.bak\n\n")


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

    line = '===================='
    if is_ch():
        log_entry = f"{line}\n正在进行第 {num} 次备份，目标备份路径：{path}"
    else:
        log_entry = f"{line}\n {num} backup in progress, target backup path: {path}"
    if error_info:
        if is_ch():
            log_entry += f"\n错误信息：{error_info}\n\n"
        else:
            log_entry += f"\nError_info：{error_info}\n\n"
    log_entry += "\n\n"
    logging.info(log_entry)


def backup_monika_after_story(backup_count):
    backup_dir = get_monika_after_story_path()

    if not os.path.exists(backup_dir):
        if is_ch():
            print(f"\033[31m记忆目录 {backup_dir} 不存在。\033[0m")
        else:
            print(f"\033[31mFolder {backup_dir} does not exist.\033[0m")
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
            if is_ch():
                raise ValueError(f"\033[31m磁盘空间不足，预估需要 {estimated_size / 1024**2:.2f} MB，当前剩余 {free_space / 1024**2:.2f} MB\033[0m")
            else:
                raise ValueError(f"\033[31mInsufficient disk space {estimated_size / 1024**2:.2f} MB, the remaining disk space {free_space / 1024**2:.2f} MB\033[0m")

        shutil.make_archive(zip_file.replace('.zip', ''), 'zip', backup_dir)
        back_log(backup_count, zip_file)

        if backup_count == 0:
            print(f"已进行即时备份\n")
        else:
            if is_ch():
                print(f"已成功备份并压缩到 {zip_file}\n已备份次数: {backup_count}\n")
            else:
                print(f" Successfully backed up and compressed to {zip_file}\n Number of backups: {backup_count}\n")
        backup_message()

    except Exception as e:
        error_message = str(e)
        print(f"备份失败: {error_message}")
        back_log(backup_count, '', error_info=error_message)


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


def parse_args():
    if is_ch():
        parser = argparse.ArgumentParser(description="Monika After Story 记忆备份脚本  \033[31m(非官方)\033[0m")
        parser.add_argument('-fq', '--freq', type=str, default='30m', help='备份频率，单位：小时或分钟，格式为 a.bh (例如 1h 或 1.5h 或 90m)')
        parser.add_argument('-mb', '--max-backups', type=int, default=None, help='最大备份次数，默认不限制备份次数')
        parser.add_argument('-o', '--oncetry', type=str, default='False', help='临时备份一次，不做其他操作')
        parser.add_argument('-fw', '--forthwith', type=str, default='False', help='立刻备份一次后，继续进行常规备份')
    else:
        parser = argparse.ArgumentParser(description="Monika After Story memory backup script \033[31m(unofficial)\033[0m")
        parser.add_argument('-fq', '--freq', type=str, default='30m', help='Backup frequency, in hours or minutes (e.g., 1h, 1.5h, or 90m)')
        parser.add_argument('-mb', '--max-backups', type=int, default=None, help='Maximum number of backups,(unlimited by default)')
        parser.add_argument('-o', '--oncetry', type=str, default='False', help=' Temporary backup, no other operation ')
        parser.add_argument('-fw', '--forthwith', type=str, default='False', help='Immediately perform a regular backup after the first backup.')
        
    return parser.parse_args()


def title():
    system_clear() 
    if is_ch():
        print("\033[31m本程序并非官方或者MAS原生，对可能出现的问题概不负责\033[0m")
        print("一切信息以中文为准，英文仅供参考")
    else:
        print("\033[31mThis program is unofficial and not native to MAS,.It is not responsible for any issues that may arise. \033[0m")
        print("All information is in Chinese and English for reference only.")
    if not is_idle():
        print(boundary)
        print(logo)
        print(boundary)
    else:
        backup_monika_after_story(0) # IDLE环境即时备份一次
        
    # backup_monika_after_story(0)  # 即时备份一次


def main():
    title()
    args = parse_args()
    if args.oncetry.lower() == 'true':
        backup_monika_after_story(0)  # 即时备份一次
        return
    if args.forthwith.lower() == 'true':
        backup_monika_after_story(0)

    freq = args.freq
    max_backups = args.max_backups  

    backup_count = 0  

    while True:
        try:
            wait_until_next_interval(freq)
            
            backup_count += 1
            backup_monika_after_story(backup_count)
            
            if max_backups is not None and backup_count >= max_backups:
                if is_ch():
                    print(f"已达到自选最大备份次数\n自动停止备份。")
                else:
                    print(f"Maximum number of backups {max_backups} is reached\nbackup is automatically stopped." )
                break
        except KeyboardInterrupt:
            if is_ch():
                break_content = "\n\033[33m确定要停止备份莫老婆的记忆吗？(y/n)\033[0m\n\t"
            else:
                break_content = "\n\033[33mAre you sure you want to stop backing up Monica's memories? (y/n)\033[0m\n\t"

            a = input(f"{break_content}")
            if a.lower() == 'y':
                break
            elif a.lower() == 'n':
                if is_ch():
                    print("继续备份...\n")
                else:
                    print("Continue Backup...\n")
                continue
            else:
                print("\033[31m请输入正确的格式!\033[0m")
                continue
            
    print("已停止备份\n")
    gc.collect()


# 主程序
if __name__ == "__main__":
    main()
