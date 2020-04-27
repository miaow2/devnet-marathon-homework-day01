import asyncio
import datetime
import netdev
import os
import re
import textfsm
import yaml

async def task(param, path, ntp_commands):
    async with netdev.create(**param) as ios:
        # выполняем необходимые команды
        data = dict()
        show_version_raw = await ios.send_command('show version')
        config = await ios.send_command('show running-config')
        show_cdp = await ios.send_command("show cdp neighbors")
        await ios.send_config_set(ntp_commands)
        show_ntp = await ios.send_command("show ntp status")

        with open(f"{path}/templates/show_version.textfsm") as f:
            re_table = textfsm.TextFSM(f)
            show_version = re_table.ParseText(show_version_raw)

        # записываем инфу для вывода
        data["hostname"] = show_version[0][2]
        data["model"] = show_version[0][3]
        data["software"] = f"{show_version[0][0]} {show_version[0][1]}"

        # выяснем NPE или PE
        if re.search(r"NPE", data["software"]):
            data["payload"] = "NPE"
        else:
            data["payload"] = "PE"

        # проверяем cdp
        if re.search(r"cdp\s+is\s+not\s+enabled", show_cdp, re.IGNORECASE):
            data["cdp_status"] = "CDP is OFF"
            data["cdp_peers"] = "0 peers"
        else:
            data["cdp_status"] = "CDP is ON"
            peers = re.search(r"total\s+cdp\s+entries\s+displayed\s*:\s*(\d+)", show_cdp, re.IGNORECASE)
            data["cdp_peers"] = f"{peers.group(1)} peers"

        # проверяем ntp
        if re.search(r"clock\s+is\s+unsynch", show_ntp, re.IGNORECASE):
            data["ntp_status"] = "Clock not Sync"
        elif re.search(r"clock\s+is\s+synch", show_ntp, re.IGNORECASE):
            data["ntp_status"] = "Clock in Sync"
        elif re.search(r"ntp\s+is\s+not\s+enabled", show_ntp, re.IGNORECASE):
            data["ntp_status"] = "Clock not Sync"

        # делаем бэкап
        backup_path = os.path.join(path, 'backups')
        now = datetime.datetime.now()
        if not os.path.exists(backup_path):
            os.mkdir(backup_path)
        with open(f"{backup_path}/{data['hostname']}-{now.strftime('%Y_%m_%d-%H_%M_%S')}.conf", "w") as input:
            input.write(config)
        print(f"{data['hostname']}|{data['model']}|{data['software']}|{data['payload']}|{data['cdp_status']}, {data['cdp_peers']}|{data['ntp_status']}")

async def run():
    # настройка ntp
    ntp_commands = ['timezone GMT 0', 'ntp server 1.1.1.1']

    # определяем путь до скрипта для упрощения навигации
    script_path = os.path.split(os.path.realpath(__file__))[0]
    with open(f"{script_path}/devices.yaml") as input:
        device_list = yaml.safe_load(input)

    # асинхронный запуск
    tasks = [task(dev, script_path, ntp_commands) for dev in device_list]
    await asyncio.wait(tasks)

loop = asyncio.get_event_loop()
loop.run_until_complete(run())
