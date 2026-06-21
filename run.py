import os
from app import create_app, db

app = create_app()


@app.cli.command('init-db')
def init_db():
    db.create_all()
    print('Database initialized.')


if __name__ == '__main__':
    debug = os.getenv('FLASK_DEBUG', 'true').lower() == 'true'
    app.run(debug=debug, port=int(os.getenv('PORT', 5000)))
