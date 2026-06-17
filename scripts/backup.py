#!/usr/bin/env python3
"""
数据库备份脚本
支持MySQL数据库和ChromaDB向量数据库的备份
"""

import os
import sys
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

# 配置
BACKUP_DIR = Path("backups")
MAX_BACKUPS = 7  # 保留最近7天的备份

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


def create_backup_dir():
    """创建备份目录"""
    BACKUP_DIR.mkdir(exist_ok=True)
    return BACKUP_DIR


def backup_mysql():
    """备份MySQL数据库"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUP_DIR / f"mysql_{timestamp}.sql"
    
    cmd = [
        "mysqldump",
        f"--host={DB_CONFIG['host']}",
        f"--port={DB_CONFIG['port']}",
        f"--user={DB_CONFIG['user']}",
        f"--password={DB_CONFIG['password']}",
        "--single-transaction",
        "--routines",
        "--triggers",
        DB_CONFIG['database'],
    ]
    
    try:
        with open(backup_file, "w", encoding="utf-8") as f:
            subprocess.run(cmd, stdout=f, check=True, stderr=subprocess.PIPE)
        print(f"✓ MySQL备份成功: {backup_file}")
        return backup_file
    except subprocess.CalledProcessError as e:
        print(f"✗ MySQL备份失败: {e}")
        return None
    except FileNotFoundError:
        print("✗ mysqldump命令未找到，请确保MySQL客户端已安装")
        return None


def backup_chromadb():
    """备份ChromaDB向量数据库"""
    if not CHROMA_DIR.exists():
        print(f"✗ ChromaDB目录不存在: {CHROMA_DIR}")
        return None
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUP_DIR / f"chromadb_{timestamp}.tar.gz"
    
    try:
        # 使用tar命令压缩
        cmd = ["tar", "-czf", str(backup_file), "-C", str(CHROMA_DIR.parent), CHROMA_DIR.name]
        subprocess.run(cmd, check=True, stderr=subprocess.PIPE)
        print(f"✓ ChromaDB备份成功: {backup_file}")
        return backup_file
    except subprocess.CalledProcessError as e:
        print(f"✗ ChromaDB备份失败: {e}")
        return None
    except FileNotFoundError:
        # Windows系统可能没有tar命令，使用shutil
        try:
            shutil.make_archive(
                str(backup_file).replace('.tar.gz', ''),
                'gztar',
                str(CHROMA_DIR.parent),
                CHROMA_DIR.name
            )
            print(f"✓ ChromaDB备份成功: {backup_file}")
            return backup_file
        except Exception as e2:
            print(f"✗ ChromaDB备份失败: {e2}")
            return None


def cleanup_old_backups():
    """清理旧备份文件"""
    if not BACKUP_DIR.exists():
        return
    
    # 获取所有备份文件
    backups = sorted(BACKUP_DIR.glob("*.sql")) + sorted(BACKUP_DIR.glob("*.tar.gz"))
    
    # 按时间排序，删除旧的
    if len(backups) > MAX_BACKUPS * 2:  # MySQL + ChromaDB
        for old_backup in backups[:len(backups) - MAX_BACKUPS * 2]:
            old_backup.unlink()
            print(f"  删除旧备份: {old_backup.name}")


def main():
    """主函数"""
    print("=" * 50)
    print("AI职业决策支持系统 - 数据库备份")
    print("=" * 50)
    print(f"备份时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 创建备份目录
    create_backup_dir()
    
    # 备份MySQL
    print("[1/3] 备份MySQL数据库...")
    mysql_file = backup_mysql()
    
    # 备份ChromaDB
    print("[2/3] 备份ChromaDB向量数据库...")
    chroma_file = backup_chromadb()
    
    # 清理旧备份
    print("[3/3] 清理旧备份...")
    cleanup_old_backups()
    
    # 统计
    print()
    print("=" * 50)
    if mysql_file and chroma_file:
        print("✓ 备份完成！")
    elif mysql_file or chroma_file:
        print("⚠ 部分备份成功")
    else:
        print("✗ 备份失败")
    
    # 显示备份目录大小
    if BACKUP_DIR.exists():
        total_size = sum(f.stat().st_size for f in BACKUP_DIR.rglob("*") if f.is_file())
        print(f"备份目录大小: {total_size / 1024 / 1024:.2f} MB")
    print("=" * 50)


if __name__ == "__main__":
    main()
