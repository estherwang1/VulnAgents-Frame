#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""端口扫描工具"""

import socket
import concurrent.futures
from typing import List


def parse_ports(ports_str: str) -> List[int]:
    """解析端口字符串"""
    ports = []
    for part in ports_str.split(','):
        part = part.strip()
        if '-' in part:
            start, end = part.split('-')
            ports.extend(range(int(start), int(end) + 1))
        else:
            ports.append(int(part))
    return list(set(ports))


def scan_port(host: str, port: int, timeout: float) -> tuple:
    """扫描单个端口"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return port, result == 0
    except:
        return port, False


def run(target: str, ports: str = None, timeout: float = 1.0, threads: int = 20, **kwargs) -> dict:
    """
    执行端口扫描
    
    Args:
        target: 目标地址
        ports: 端口列表
        timeout: 超时时间
        threads: 线程数
    
    Returns:
        扫描结果
    """
    if ports is None:
        ports = "21,22,23,25,53,80,110,143,443,445,993,995,1433,3306,3389,5432,6379,8080,8443,9000"
    
    port_list = parse_ports(ports)
    open_ports = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
        futures = {executor.submit(scan_port, target, p, timeout): p for p in port_list}
        for future in concurrent.futures.as_completed(futures):
            port, is_open = future.result()
            if is_open:
                open_ports.append(port)
    
    open_ports.sort()
    
    return {
        "target": target,
        "open_ports": open_ports,
        "scanned_count": len(port_list),
        "open_count": len(open_ports)
    }
