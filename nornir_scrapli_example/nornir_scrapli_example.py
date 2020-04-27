import datetime
import os
import re

from nornir import InitNornir
from nornir.plugins.tasks.files import write_file
from nornir_scrapli.tasks import send_command, send_configs
from nornir.plugins.tasks.text import template_file

from pprint import pprint


def get_backup(task, path):
    backup = task.run(task=send_command, command='show running-config')
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
    show_version = task.run(task=send_command, command='show version')
    data = show_version.scrapli_response.genie_parse_output()
    pprint(data)
    task.host["hostname"] = data["version"]["hostname"]
    task.host["model"] = data["version"]["chassis"]
    task.host["software"] = f'{data["version"]["image_id"]} {data["version"]["version"]}'
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
    task.run(task=send_configs, configs=commands)
    task.run(task=send_command, command='write memory')


def check_ntp(task):
    ntp_status = task.run(task=send_command, command='show ntp status')
    data = ntp_status.scrapli_response.genie_parse_output()
    if data:
        if data["clock_state"]["system_status"]["status"] == "synchronized":
            task.host["ntp_status"] = "Clock in Sync"
        else:
            task.host["ntp_status"] = "Clock not Sync"
    else:
        task.host["ntp_status"] = "Clock not Sync"


def check_cdp(task):
    cdp_status = task.run(task=send_command, command='show cdp neighbors')
    data = cdp_status.scrapli_response.genie_parse_output()
    if data:
            task.host["cdp_status"] = "CDP is ON"
            task.host["cdp_peers"] = f"{len(data['cdp']['index'])} peers"
    else:
        task.host["cdp_status"] = "CDP is OFF"
        task.host["cdp_peers"] = "0 peers"


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
        print(value)
        print(f"{value['data']['hostname']}|{value['data']['model']}|{value['data']['software']}|{value['data']['payload']}|{value['data']['cdp_status']}, {value['data']['cdp_peers']}|{value['data']['ntp_status']}")


if __name__ == '__main__':
    main()