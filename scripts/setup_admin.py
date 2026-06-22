import os
import sys

# 将项目根目录添加到 python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.user import User
from sqlalchemy import text

def setup_admin():
    app = create_app()
    with app.app_context():
        # 1. 检测并添加 is_admin 字段到 users 表
        engine = db.engine
        print("正在检查数据库结构...")

        try:
            with engine.connect() as conn:
                # 检查 is_admin 列是否存在
                result = conn.execute(text("SHOW COLUMNS FROM users LIKE 'is_admin'"))
                columns = result.fetchall()

                if not columns:
                    print("未检测到 is_admin 字段，正在升级 users 表...")
                    # 执行 ALTER TABLE
                    conn.execute(text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE"))
                    conn.commit()
                    print("成功向 users 表添加 is_admin 字段！")
                else:
                    print("users 表中已存在 is_admin 字段。")
        except Exception as e:
            print(f"检查或更新数据库表结构时出错: {e}")
            print("尝试使用 db.create_all() ...")
            try:
                db.create_all()
                print("db.create_all() 执行成功。")
            except Exception as ex:
                print(f"db.create_all() 失败: {ex}")
                sys.exit(1)

        # 2. 检查或创建默认管理员账号（从环境变量读取凭据）
        print("\n正在检查默认管理员账号...")
        admin_username = os.getenv("ADMIN_USERNAME", "admin")
        admin_email = os.getenv("ADMIN_EMAIL", "admin@career.ai")
        admin_pass = os.getenv("ADMIN_PASSWORD")

        if not admin_pass:
            print("[ERROR] 未设置 ADMIN_PASSWORD 环境变量！")
            print("请在 .env 文件中配置：")
            print("  ADMIN_USERNAME=admin")
            print("  ADMIN_PASSWORD=<你的安全密码>")
            print("  ADMIN_EMAIL=admin@career.ai")
            sys.exit(1)

        admin_user = User.query.filter_by(username=admin_username).first()
        if not admin_user:
            print(f"管理员账号 '{admin_username}' 不存在，正在创建...")
            admin_user = User(
                username=admin_username,
                email=admin_email,
                is_admin=True,
                is_active=True
            )
            admin_user.set_password(admin_pass)
            db.session.add(admin_user)
            db.session.commit()
            print(f"成功创建默认管理员！")
            print(f"用户名: {admin_username}")
            print(f"邮  箱: {admin_email}")
            print("请登录后及时更改密码！")
        else:
            print(f"管理员账号 '{admin_username}' 已存在。")
            if not admin_user.is_admin:
                print(f"正在将 '{admin_username}' 用户升级为管理员...")
                admin_user.is_admin = True
                db.session.commit()
                print("升级成功！")
            else:
                print("该账号已具备管理员权限。")

if __name__ == "__main__":
    setup_admin()
