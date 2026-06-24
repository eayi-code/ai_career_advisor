#!/usr/bin/env python3
"""SSH更新脚本"""

import paramiko

def ssh_execute(host, user, password, command, timeout=120):
    """SSH执行命令"""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        client.connect(host, username=user, password=password, timeout=timeout)
        
        # 使用sudo -S传递密码
        if command.startswith('sudo '):
            cmd = command[5:]
            command = f'echo "{password}" | sudo -S bash -c "{cmd}"'
        
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
    
    # 更新命令
    commands = [
        ('cd /home/eayi/ai_career_advisor && git pull', '拉取最新代码'),
        ('cd /home/eayi/ai_career_advisor && docker-compose -f docker-compose.lan.yml up -d --build', '重新构建并重启'),
        ('cd /home/eayi/ai_career_advisor && docker-compose -f docker-compose.lan.yml ps', '查看服务状态'),
    ]
    
    for cmd, desc in commands:
        print(f"\n[{desc}]")
        print(f"执行: {cmd}")
        output, error = ssh_execute(host, user, password, cmd)
        
        if output:
            print(f"输出:\n{output}")
        if error:
            print(f"错误:\n{error}")

if __name__ == "__main__":
    main()
