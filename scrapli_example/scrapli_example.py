import datetime
import multiprocessing as mp
import sys
import os
import re
import yaml

from pprint import pprint
from scrapli.driver.core import IOSXEDriver

NTP_COMMANDS = ['timezone GMT 0', 'ntp server 1.1.1.1']


def gather_info(device, path):
    data = dict()
    conn = IOSXEDriver(**device)
    conn.open()
    # выполняем необходимые команды
    show_version = conn.send_command("show version")
    config = conn.send_command("show running-config")
    show_cdp = conn.send_command("show cdp neighbors")
    conn.send_configs(NTP_COMMANDS)
    show_ntp = conn.send_command("show ntp status")
    conn.close()

    # записываем инфу для вывода
    data["hostname"] = re.search(r"\s*(\S+)\s+uptime\s+is", show_version.result).group(1)
    data["model"] = re.search(r"[Cc]isco\s+(\S+)\s+\(", show_version.result).group(1)
    data["software"] = re.search(r".*Software\s+\((?P<package>\S+)\),\s+Version\s+(?P<version>\S+),\s+", show_version.result).groupdict()

    # выяснем NPE или PE
    if re.search(r"NPE", data["software"]["package"]):
        data["payload"] = "NPE"
    else:
        data["payload"] = "PE"

    # делаем бэкап
    backup_path = os.path.join(path, 'backups')
    now = datetime.datetime.now()
    if not os.path.exists(backup_path):
        os.mkdir(backup_path)
    with open(f"{backup_path}/{data['hostname']}-{now.strftime('%Y_%m_%d-%H_%M_%S')}.conf", "w") as input:
        input.write(config.result)

    # проверяем cdp
    if re.search(r"cdp\s+is\s+not\s+enabled", show_cdp.result, re.IGNORECASE):
        data["cdp_status"] = "CDP is OFF"
        data["cdp_peers"] = "0 peers"
    else:
        data["cdp_status"] = "CDP is ON"
        peers = re.search(r"total\s+cdp\s+entries\s+displayed\s*:\s*(\d+)", show_cdp.result, re.IGNORECASE)
        data["cdp_peers"] = f"{peers.group(1)} peers"
    
    # проверяем ntp
    if re.search(r"clock\s+is\s+unsynch", show_ntp.result, re.IGNORECASE):
        data["ntp_status"] = "Clock not Sync"
    elif re.search(r"clock\s+is\s+synch", show_ntp.result, re.IGNORECASE):
        data["ntp_status"] = "Clock in Sync"
    elif re.search(r"ntp\s+is\s+not\s+enabled", show_ntp.result, re.IGNORECASE):
        data["ntp_status"] = "Clock not Sync"
    print(f"{data['hostname']}|{data['model']}|{data['software']['package']} {data['software']['version']}|{data['payload']}|{data['cdp_status']}, {data['cdp_peers']}|{data['ntp_status']}")



def main():
    # определяем путь до скрипта для упрощения навигации
    script_path = os.path.split(os.path.realpath(__file__))[0]
    with open(f"{script_path}/devices.yaml") as input:
        device_list = yaml.safe_load(input)

    # запуск через multiprocessing
    processes=list()

    with mp.Pool(4) as pool:
        for device in device_list:
            processes.append(pool.apply_async(gather_info, args=(device, script_path)))
        for process in processes:
            process.get()


if __name__ == '__main__':
    main()