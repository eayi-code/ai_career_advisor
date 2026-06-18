#!/usr/bin/env python3
"""SSH自动部署脚本"""

import paramiko
import sys
import time

def ssh_execute(host, user, password, command, timeout=60):
    """SSH执行命令"""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        client.connect(host, username=user, password=password, timeout=timeout)
        
        # 使用sudo -S传递密码
        if command.startswith('sudo '):
            cmd = command[5:]
            command = f'echo "{password}" | sudo -S bash -c "{cmd}"'
        
        # 获取伪终端
        transport = client.get_transport()
        channel = transport.open_session()
        channel.get_pty()
        channel.exec_command(command)
        
        output = channel.recv(65535).decode('utf-8')
        error = channel.recv_stderr(65535).decode('utf-8')
        
        return output, error
    except Exception as e:
        return None, str(e)
    finally:
        client.close()

def main():
    host = "10.43.84.249"
    user = "eayi"
    password = "333666"
    
    # 部署命令
    commands = [
        # 1. 配置DNS
        ('echo "nameserver 223.5.5.5" | sudo tee /etc/resolv.conf', '配置DNS'),
        ('echo "nameserver 114.114.114.114" | sudo tee -a /etc/resolv.conf', '添加备用DNS'),
        
        # 2. 测试网络
        ('ping -c 3 baidu.com', '测试网络'),
        
        # 3. 安装Docker
        ('sudo apt update', '更新软件源'),
        ('sudo apt install -y docker.io docker-compose', '安装Docker'),
        
        # 4. 启动Docker
        ('sudo systemctl start docker', '启动Docker'),
        ('sudo systemctl enable docker', '设置Docker开机自启'),
        
        # 5. 进入项目目录
        ('cd ~/ai_career_advisor && ls', '检查项目目录'),
        
        # 6. 启动服务
        ('cd ~/ai_career_advisor && sudo docker-compose -f docker-compose.lan.yml up -d', '启动服务'),
        
        # 7. 检查服务状态
        ('cd ~/ai_career_advisor && sudo docker-compose -f docker-compose.lan.yml ps', '检查服务状态'),
    ]
    
    for cmd, desc in commands:
        print(f"\n[{desc}]")
        print(f"执行: {cmd}")
        output, error = ssh_execute(host, user, password, cmd)
        
        if output:
            print(f"输出: {output[:500]}")
        if error:
            print(f"错误: {error[:500]}")
        
        time.sleep(2)

if __name__ == "__main__":
    main()
