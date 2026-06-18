#!/usr/bin/env python3
"""SSH自动连接脚本"""

import subprocess
import sys

def ssh_connect(host, user, password, command):
    """使用SSH连接并执行命令"""
    # 使用plink（PuTTY）或ssh
    try:
        # 尝试使用plink
        cmd = f'echo {password} | plink -ssh {user}@{host} "{command}"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return result.stdout, result.stderr
    except:
        pass
    
    try:
        # 尝试使用ssh（需要安装sshpass）
        cmd = f'sshpass -p {password} ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no {user}@{host} "{command}"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return result.stdout, result.stderr
    except:
        pass
    
    return None, "无法连接"

if __name__ == "__main__":
    host = "10.43.84.249"
    user = "eayi"
    password = "333666"
    
    # 测试连接
    stdout, stderr = ssh_connect(host, user, password, "whoami")
    if stdout:
        print(f"连接成功: {stdout}")
    else:
        print(f"连接失败: {stderr}")
