#!/usr/bin/env python3
"""
健康检查脚本
用于监控应用状态，支持Docker健康检查
"""

import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime


def check_api(base_url="http://localhost:5000"):
    """检查API健康状态"""
    try:
        url = f"{base_url}/api/test"
        req = urllib.request.Request(url, method="GET")
        req.add_header("Content-Type", "application/json")
        
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            return {
                "status": "healthy" if data.get("code") == 200 else "unhealthy",
                "response_time": response.headers.get("X-Response-Time", "N/A"),
                "version": data.get("version", "unknown"),
            }
    except urllib.error.URLError as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }


def check_database():
    """检查数据库连接"""
    try:
        # 尝试导入并连接数据库
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from app import create_app, db
        
        app = create_app()
        with app.app_context():
            # 执行简单查询
            result = db.session.execute(db.text("SELECT 1")).scalar()
            return {
                "status": "healthy" if result == 1 else "unhealthy",
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }


def check_chromadb():
    """检查ChromaDB连接"""
    try:
        chroma_dir = os.getenv("CHROMA_PERSIST_DIR", "./chroma_data")
        if os.path.exists(chroma_dir):
            return {"status": "healthy"}
        else:
            return {"status": "unhealthy", "error": "ChromaDB directory not found"}
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }


def main():
    """主函数"""
    base_url = os.getenv("APP_URL", "http://localhost:5000")
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "api": check_api(base_url),
        "database": check_database(),
        "chromadb": check_chromadb(),
    }
    
    # 判断整体状态
    all_healthy = all(
        r.get("status") == "healthy" 
        for r in [results["api"], results["database"], results["chromadb"]]
    )
    results["overall"] = "healthy" if all_healthy else "unhealthy"
    
    # 输出结果
    print(json.dumps(results, indent=2, ensure_ascii=False))
    
    # 返回状态码
    sys.exit(0 if all_healthy else 1)


if __name__ == "__main__":
    main()
