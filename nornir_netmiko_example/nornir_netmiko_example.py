import datetime
import os
import re

from nornir import InitNornir
from nornir.plugins.tasks.files import write_file
from nornir.plugins.tasks.networking import netmiko_send_config, netmiko_send_command
from nornir.plugins.tasks.text import template_file


def get_backup(task, path):
    backup = task.run(task=netmiko_send_command, command_string='show running-config')
    backup_path = os.path.join(path, 'backups')
    now = datetime.datetime.now()
    if not os.path.exists(backup_path):
        os.mkdir(backup_path)
    task.run(
        task=write_file,
        content=backup.result,
        filename=f"{backup_path}/{task.host['hostname']}-{now.strftime('%Y_%m_%d-%H_%M_%S')}.conf"
    )


def get_version(task, path):
    show_version = task.run(
        task=netmiko_send_command,
        command_string='show version',
        use_textfsm=True,
        textfsm_template=f"{path}/templates/show_version.textfsm"
    )
    task.host["hostname"] = show_version.result[0]["hostname"]
    task.host["model"] = show_version.result[0]["hardware"]
    task.host["software"] = f'{show_version.result[0]["software"]} {show_version.result[0]["version"]}'
    if re.search(r"NPE", task.host["software"]):
        task.host["payload"] = "NPE"
    else:
        task.host["payload"] = "PE"


def configure_ntp(task, path):
    render_commands = task.run(
        task=template_file,
        template="ntp.j2",
        path=f"{path}/templates/"
    )
    commands = render_commands.result.splitlines()
    task.run(task=netmiko_send_config, config_commands=commands)
    task.run(task=netmiko_send_command, command_string='write memory')


def check_ntp(task):
    ntp_status = task.run(task=netmiko_send_command, command_string='show ntp status')
    if re.search(r"clock\s+is\s+unsynch", ntp_status.result, re.IGNORECASE):
        task.host["ntp_status"] = "Clock not Sync"
    elif re.search(r"clock\s+is\s+synch", ntp_status.result, re.IGNORECASE):
        task.host["ntp_status"] = "Clock in Sync"
    elif re.search(r"ntp\s+is\s+not\s+enabled", ntp_status.result, re.IGNORECASE):
        task.host["ntp_status"] = "Clock not Sync"


def check_cdp(task):
    cdp_status = task.run(task=netmiko_send_command, command_string='show cdp neighbors')
    if re.search(r"cdp\s+is\s+not\s+enabled", cdp_status.result, re.IGNORECASE):
        task.host["cdp_status"] = "CDP is OFF"
        task.host["cdp_peers"] = "0 peers"
    else:
        task.host["cdp_status"] = "CDP is ON"
        peers = re.search(r"total\s+cdp\s+entries\s+displayed\s*:\s*(\d+)", cdp_status.result, re.IGNORECASE)
        task.host["cdp_peers"] = f"{peers.group(1)} peers"


def main():
    # определяем путь до скрипта для упрощения навигации
    script_path = os.path.split(os.path.realpath(__file__))[0]
    # иницилизируем норнир
    nr = InitNornir(
        core={"num_workers": 20},
        logging={"enabled": False},
        inventory={
            "plugin": "nornir.plugins.inventory.simple.SimpleInventory",
            "options": {
                "host_file": f"{script_path}/devices.yaml",
            }
        }
    )
    # получаем инфу об обуродовании
    nr.run(task=get_version, path=script_path)

    # делаем бэкап
    nr.run(task=get_backup, path=script_path)

    # конфигурим ntp
    nr.run(task=configure_ntp, path=script_path)

    # проверяем ntp
    nr.run(task=check_ntp)

    # првоеряем cdp
    nr.run(task=check_cdp)

    # выводим на экран инфу
    for value in nr.inventory.dict()['hosts'].values():
        print(f"{value['data']['hostname']}|{value['data']['model']}|{value['data']['software']}|{value['data']['payload']}|{value['data']['cdp_status']}, {value['data']['cdp_peers']}|{value['data']['ntp_status']}")


if __name__ == '__main__':
    main()