# Домашная работа первый день DevNet Marathon

В каждой папке реализация при помощи разных фреймворков, в файлах `devices.yaml` указываются девайсы для подключения
Необходимо установить все библиотеки из [requirements.txt](https://github.com/miaow2/devnet-marathon-homework-day01/blob/master/requirements.txt).

Проверялось на Cisco IOS-XE

* [Netdev](https://github.com/selfuryon/netdev) c [AsyncSSH](https://asyncssh.readthedocs.io/en/latest/), [TextFSM](https://github.com/google/textfsm/wiki/TextFSM)
* [Nornir](https://github.com/nornir-automation/nornir) + [Netmiko](https://github.com/ktbyers/netmiko) c [Paramiko](http://www.paramiko.org/), [TextFSM](https://github.com/google/textfsm/wiki/TextFSM) и [Jinja2](https://jinja.palletsprojects.com/)
* [Nornir](https://github.com/nornir-automation/nornir) + [Scrapli](https://github.com/carlmontanari/nornir_scrapli) c [SSH2-Python](https://github.com/ParallelSSH/ssh2-python), [Genie](https://pubhub.devnetcloud.com/media/genie-feature-browser/docs/)  и [Jinja2](https://jinja.palletsprojects.com/)
* [Scrapli](https://github.com/carlmontanari/scrapli) c [SSH2-Python](https://github.com/ParallelSSH/ssh2-python)
