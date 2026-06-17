#!/usr/bin/env python3
"""
数据库恢复脚本
支持MySQL数据库和ChromaDB向量数据库的恢复
"""

import os
import sys
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

# 配置
BACKUP_DIR = Path("backups")

# 数据库配置
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "3306"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "password"),
    "database": os.getenv("DB_NAME", "career_advisor"),
}

# ChromaDB配置
CHROMA_DIR = Path(os.getenv("CHROMA_PERSIST_DIR", "./chroma_data"))


def list_backups():
    """列出所有备份文件"""
    if not BACKUP_DIR.exists():
        print("✗ 备份目录不存在")
        return []
    
    backups = []
    
    # MySQL备份
    for f in sorted(BACKUP_DIR.glob("mysql_*.sql"), reverse=True):
        backups.append({
            "type": "mysql",
            "file": f,
            "time": f.stem.replace("mysql_", ""),
            "size": f.stat().st_size / 1024 / 1024
        })
    
    # ChromaDB备份
    for f in sorted(BACKUP_DIR.glob("chromadb_*.tar.gz"), reverse=True):
        backups.append({
            "type": "chromadb",
            "file": f,
            "time": f.stem.replace("chromadb_", ""),
            "size": f.stat().st_size / 1024 / 1024
        })
    
    return backups


def restore_mysql(backup_file):
    """恢复MySQL数据库"""
    if not backup_file.exists():
        print(f"✗ 备份文件不存在: {backup_file}")
        return False
    
    cmd = [
        "mysql",
        f"--host={DB_CONFIG['host']}",
        f"--port={DB_CONFIG['port']}",
        f"--user={DB_CONFIG['user']}",
        f"--password={DB_CONFIG['password']}",
        DB_CONFIG['database'],
    ]
    
    try:
        with open(backup_file, "r", encoding="utf-8") as f:
            subprocess.run(cmd, stdin=f, check=True, stderr=subprocess.PIPE)
        print(f"✓ MySQL恢复成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ MySQL恢复失败: {e}")
        return False
    except FileNotFoundError:
        print("✗ mysql命令未找到，请确保MySQL客户端已安装")
        return False


def restore_chromadb(backup_file):
    """恢复ChromaDB向量数据库"""
    if not backup_file.exists():
        print(f"✗ 备份文件不存在: {backup_file}")
        return False
    
    # 备份当前数据
    if CHROMA_DIR.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_current = CHROMA_DIR.parent / f"{CHROMA_DIR.name}_backup_{timestamp}"
        shutil.copytree(CHROMA_DIR, backup_current)
        print(f"  当前数据已备份到: {backup_current}")
        
        # 删除当前数据
        shutil.rmtree(CHROMA_DIR)
    
    try:
        # 解压备份
        if backup_file.name.endswith('.tar.gz'):
            cmd = ["tar", "-xzf", str(backup_file), "-C", str(CHROMA_DIR.parent)]
            subprocess.run(cmd, check=True, stderr=subprocess.PIPE)
        else:
            shutil.unpack_archive(str(backup_file), str(CHROMA_DIR.parent))
        
        print(f"✓ ChromaDB恢复成功")
        return True
    except Exception as e:
        print(f"✗ ChromaDB恢复失败: {e}")
        return False


def main():
    """主函数"""
    print("=" * 50)
    print("AI职业决策支持系统 - 数据库恢复")
    print("=" * 50)
    print()
    
    # 列出备份
    backups = list_backups()
    
    if not backups:
        print("没有找到备份文件")
        return
    
    # 显示备份列表
    print("可用的备份文件:")
    print("-" * 50)
    for i, backup in enumerate(backups, 1):
        print(f"{i}. [{backup['type'].upper()}] {backup['time']} ({backup['size']:.2f} MB)")
    print("-" * 50)
    
    # 用户选择
    try:
        choice = int(input("\n请选择要恢复的备份编号 (0 取消): "))
        if choice == 0:
            print("已取消")
            return
        
        if choice < 1 or choice > len(backups):
            print("无效的选择")
            return
        
        selected = backups[choice - 1]
        
        # 确认
        print(f"\n即将恢复: [{selected['type'].upper()}] {selected['time']}")
        confirm = input("此操作会覆盖当前数据，是否继续? (y/N): ")
        
        if confirm.lower() != 'y':
            print("已取消")
            return
        
        # 执行恢复
        print("\n开始恢复...")
        
        if selected['type'] == 'mysql':
            success = restore_mysql(selected['file'])
        else:
            success = restore_chromadb(selected['file'])
        
        if success:
            print("\n✓ 恢复完成！")
        else:
            print("\n✗ 恢复失败")
            
    except ValueError:
        print("无效的输入")
    except KeyboardInterrupt:
        print("\n已取消")


if __name__ == "__main__":
    main()
