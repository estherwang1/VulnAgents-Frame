#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Nmap 端口扫描工具 - 封装 nmap 命令"""

import subprocess
import xml.etree.ElementTree as ET
import shutil
from typing import Dict


def check_nmap() -> bool:
    """检查 nmap 是否安装"""
    return shutil.which("nmap") is not None


def parse_nmap_xml(xml_output: str) -> Dict:
    """解析 nmap XML 输出"""
    result = {"hosts": []}
    
    try:
        root = ET.fromstring(xml_output)
        
        for host in root.findall('host'):
            host_info = {
                "status": "unknown",
                "ip": "",
                "hostnames": [],
                "ports": [],
                "os": []
            }
            
            # 状态
            status = host.find('status')
            if status is not None:
                host_info["status"] = status.get('state')
            
            # IP 地址
            for addr in host.findall('address'):
                if addr.get('addrtype') == 'ipv4':
                    host_info["ip"] = addr.get('addr')
            
            # 主机名
            hostnames = host.find('hostnames')
            if hostnames is not None:
                for hostname in hostnames.findall('hostname'):
                    host_info["hostnames"].append(hostname.get('name'))
            
            # 端口
            ports = host.find('ports')
            if ports is not None:
                for port in ports.findall('port'):
                    state = port.find('state')
                    if state is not None and state.get('state') == 'open':
                        port_info = {
                            "port": int(port.get('portid')),
                            "protocol": port.get('protocol'),
                            "service": "",
                            "product": "",
                            "version": ""
                        }
                        
                        service = port.find('service')
                        if service is not None:
                            port_info["service"] = service.get('name', '')
                            port_info["product"] = service.get('product', '')
                            port_info["version"] = service.get('version', '')
                        
                        host_info["ports"].append(port_info)
            
            # OS 检测
            os_elem = host.find('os')
            if os_elem is not None:
                for osmatch in os_elem.findall('osmatch'):
                    host_info["os"].append({
                        "name": osmatch.get('name'),
                        "accuracy": osmatch.get('accuracy')
                    })
            
            result["hosts"].append(host_info)
    
    except ET.ParseError as e:
        result["parse_error"] = str(e)
    
    return result


def run(target: str,
        ports: str = None,
        scan_type: str = "syn",
        service_detection: bool = True,
        os_detection: bool = False,
        scripts: str = None,
        timing: int = 4,
        timeout: int = 300,
        **kwargs) -> dict:
    """
    执行 Nmap 扫描
    
    Args:
        target: 目标 IP 或域名
        ports: 端口范围（如 "22,80,443" 或 "1-1000"）
        scan_type: 扫描类型 (syn/tcp/udp/quick/ping)
        service_detection: 是否检测服务版本
        os_detection: 是否检测操作系统
        scripts: NSE 脚本（如 "vuln"）
        timing: 时间模板 0-5
        timeout: 超时时间（秒）
    
    Returns:
        扫描结果
    """
    if not check_nmap():
        return {"error": "nmap 未安装，请运行: apt install nmap"}
    
    # 构建命令
    cmd = ["nmap", "-oX", "-"]  # XML 输出到 stdout
    
    # 扫描类型
    scan_types = {
        "syn": "-sS",
        "tcp": "-sT", 
        "udp": "-sU",
        "quick": "-F",
        "ping": "-sn"
    }
    cmd.append(scan_types.get(scan_type, "-sS"))
    
    # 端口
    if ports and scan_type != "ping":
        cmd.extend(["-p", ports])
    
    # 服务检测
    if service_detection and scan_type not in ["ping", "quick"]:
        cmd.append("-sV")
    
    # OS 检测
    if os_detection:
        cmd.append("-O")
    
    # 脚本
    if scripts:
        cmd.extend(["--script", scripts])
    
    # 时间模板
    cmd.append(f"-T{timing}")
    
    # 目标
    cmd.append(target)
    
    try:
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=timeout
        )
        
        if result.returncode != 0 and not result.stdout:
            return {
                "error": result.stderr or "nmap 执行失败",
                "command": " ".join(cmd)
            }
        
        # 解析 XML
        parsed = parse_nmap_xml(result.stdout)
        
        # 简化输出
        open_ports = []
        services = []
        for host in parsed.get("hosts", []):
            for port in host.get("ports", []):
                open_ports.append(port["port"])
                if port["service"]:
                    services.append({
                        "port": port["port"],
                        "service": port["service"],
                        "product": port["product"],
                        "version": port["version"]
                    })
        
        return {
            "target": target,
            "open_ports": open_ports,
            "services": services,
            "hosts": parsed["hosts"],
            "command": " ".join(cmd)
        }
        
    except subprocess.TimeoutExpired:
        return {"error": f"扫描超时（{timeout}秒）", "command": " ".join(cmd)}
    except Exception as e:
        return {"error": str(e), "command": " ".join(cmd)}
