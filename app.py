from flask import Flask, redirect, url_for
from utils.db import init_db
from routes.auth import login, logout, change_password
from routes.materials import materials, add_material, edit_material, delete_material
from routes.transactions import purchase, sell, orders, order_detail
from routes.statistics import statistics
from routes.users import permissions, edit_user

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Đăng ký các route
app.add_url_rule('/', 'index', lambda: redirect(url_for('materials')))
app.add_url_rule('/login', 'login', login, methods=['GET', 'POST'])
app.add_url_rule('/logout', 'logout', logout)
app.add_url_rule('/change_password/<int:user_id>', 'change_password', change_password, methods=['GET', 'POST'])

app.add_url_rule('/materials', 'materials', materials)
app.add_url_rule('/add_material', 'add_material', add_material, methods=['GET', 'POST'])
app.add_url_rule('/edit_material/<int:id>', 'edit_material', edit_material, methods=['GET', 'POST'])
app.add_url_rule('/delete_material/<int:id>', 'delete_material', delete_material)

app.add_url_rule('/purchase', 'purchase', purchase, methods=['GET', 'POST'])
app.add_url_rule('/sell', 'sell', sell, methods=['GET', 'POST'])
app.add_url_rule('/orders', 'orders', orders)
app.add_url_rule('/order_detail/<int:order_id>', 'order_detail', order_detail)

app.add_url_rule('/statistics', 'statistics', statistics)

app.add_url_rule('/permissions', 'permissions', permissions, methods=['GET', 'POST'])
app.add_url_rule('/edit_user/<int:user_id>', 'edit_user', edit_user, methods=['GET', 'POST'])

if __name__ == '__main__':
    init_db()
    app.run(debug=True)