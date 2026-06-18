#!/usr/bin/env python3
"""SSH自动部署脚本"""

import paramiko
import sys

def ssh_execute(host, user, password, command, timeout=30):
    """SSH执行命令"""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        client.connect(host, username=user, password=password, timeout=timeout)
        stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        
        output = stdout.read().decode('utf-8')
        error = stderr.read().decode('utf-8')
        
        return output, error
    except Exception as e:
        return None, str(e)
    finally:
        client.close()

def main():
    host = "10.43.84.249"
    user = "eayi"
    password = "333666"
    
    if len(sys.argv) > 1:
        command = " ".join(sys.argv[1:])
    else:
        command = "whoami && hostname && uname -a"
    
    print(f"连接 {user}@{host}...")
    output, error = ssh_execute(host, user, password, command)
    
    if output:
        print("输出:")
        print(output)
    if error:
        print("错误:")
        print(error)

if __name__ == "__main__":
    main()
