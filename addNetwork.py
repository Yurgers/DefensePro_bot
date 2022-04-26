from loguru import logger

import ipaddress
from datetime import date


def generate_command_blocklist(name: str) -> str:
    disc = date.today().strftime("%Y-%m-%d")
    command = f"dp block-allow-lists blocklist table create {name} -sn {name} -a drop -d {disc}"
    # print(command)
    return command


def generate_command_allowlist(name: str, dn: str = any) -> str:
    command = f'dp block-allow-lists allowlist create {name} -sn {name} -dn {dn} -dir bi-direct -a bypass -ra no-report'
    # print(command)
    return command


def generate_command_network_classes(name: str, sub_index: int, ip: ipaddress) -> str:
    command = f'classes modify network create {name} {sub_index} -a {ip.network_address} -s {ip.prefixlen}'
    # print(command)
    return command


def check_ip(line: str) -> ipaddress:
    try:
        line = line.strip()
        ip = ipaddress.ip_network(line)
    except Exception as err:
        logger.error(f'{line}, не является адресом сети')
        return False

    return ip


def create_command(networks_list: list,
                   network_class_prefix: str,
                   start_number_class: int = 1,
                   blacklist: bool = True,
                   start_sub_index: int = -1
                   ) -> list:
    number_class = start_number_class
    sub_index = start_sub_index

    network_class_name = f'{network_class_prefix}-{number_class}'
    # logger.info(f'class={network_class_name}, {sub_index=}')

    command_list = []
    error_list = []
    for network in networks_list:
        ip = check_ip(network)

        if not ip:
            error_list.append(network)
            continue

        if sub_index < 255:
            sub_index += 1
        else:
            if blacklist:
                command_list.append(generate_command_blocklist(network_class_name))

            number_class += 1
            network_class_name = f'{network_class_prefix}-{number_class}'
            sub_index = 0

        command_list.append(generate_command_network_classes(network_class_name, sub_index, ip))

    if blacklist and sub_index > -1:
        command_list.append(generate_command_blocklist(network_class_name))

    return command_list, error_list


if __name__ == '__main__':
    logger.debug("start")

    network_class_prefix = "Ru-net"
    file_zone = 'ip_RU.lst'

    networks_list = open(file_zone).read().split()

    command_list, error_list = create_command(networks_list, network_class_prefix)
