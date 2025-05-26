import mysql.connector
from flask import Flask, render_template, request, redirect, url_for, session, flash
import matplotlib
matplotlib.use('Agg')  # Sử dụng backend Agg cho môi trường không có GUI
import matplotlib.pyplot as plt
import os
from datetime import datetime
from mysql.connector import pooling
from dotenv import load_dotenv

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Tải biến môi trường từ file .env
load_dotenv()

# Cấu hình MySQL với biến môi trường
db_config = {
    'host': os.getenv("MYSQL_HOST"),
    'user': os.getenv("MYSQL_USER"),
    'password': os.getenv("MYSQL_PASSWORD"),
    'port': int(os.getenv("MYSQL_PORT", 3306)),
    'database': os.getenv("MYSQL_DATABASE"),
    'raise_on_warnings': False,  # Tắt cảnh báo để tránh lỗi Table exists
    # Tắt SSL tạm thời
    'ssl_ca': None,
    'ssl_cert': None,
    'ssl_key': None,
    'ssl_verify_cert': False
}

# Tạo connection pool cho MySQL
connection_pool = mysql.connector.pooling.MySQLConnectionPool(
    pool_name="mypool",
    pool_size=5,  # Số lượng kết nối tối đa trong pool
    pool_reset_session=True,
    **db_config
)

# Hàm kết nối cơ sở dữ liệu từ pool
def get_db_connection():
    try:
        conn = connection_pool.get_connection()
        if conn.is_connected():
            return conn
        else:
            raise Exception("Không thể kết nối đến cơ sở dữ liệu")
    except Exception as e:
        app.logger.error(f"Lỗi kết nối cơ sở dữ liệu: {str(e)}")
        flash("Lỗi kết nối cơ sở dữ liệu. Vui lòng thử lại sau.", "error")
        return None

# Khởi tạo cơ sở dữ liệu
def init_db():
    conn = get_db_connection()
    if conn is None:
        return
    cursor = conn.cursor()
    # Kiểm tra và tạo bảng nếu chưa tồn tại
    cursor.execute('SHOW TABLES LIKE %s', ('users',))
    if not cursor.fetchone():
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(50) NOT NULL,
                role VARCHAR(50) DEFAULT 'Employee' NOT NULL,
                employee_id VARCHAR(20),
                full_name VARCHAR(100),
                phone_number VARCHAR(15)
            )
        ''')
    cursor.execute('SHOW TABLES LIKE %s', ('materials',))
    if not cursor.fetchone():
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS materials (
                id INT AUTO_INCREMENT PRIMARY KEY,
                code VARCHAR(50) UNIQUE NOT NULL,
                name VARCHAR(255) NOT NULL,
                unit VARCHAR(50),
                purchase_price DECIMAL(10, 2),
                sale_price DECIMAL(10, 2),
                supplier_id INT,
                stock INT,
                status VARCHAR(50)
            )
        ''')
    cursor.execute('SHOW TABLES LIKE %s', ('transactions',))
    if not cursor.fetchone():
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                material_id INT,
                type VARCHAR(50), -- 'purchase' hoặc 'sale'
                quantity INT,
                date DATETIME,
                employee_id VARCHAR(20),
                supplier_name VARCHAR(100),
                supplier_phone VARCHAR(15),
                customer_name VARCHAR(100),
                customer_phone VARCHAR(15),
                FOREIGN KEY (material_id) REFERENCES materials(id)
            )
        ''')
    # Chèn người dùng mặc định nếu chưa tồn tại
    cursor.execute("INSERT IGNORE INTO users (username, password, role, employee_id, full_name, phone_number) VALUES ('admin', 'admin123', 'Manager', 'NV001', 'Nguyễn Văn A', '0901234567')")
    conn.commit()
    cursor.close()
    conn.close()

# Kiểm tra quyền Manager
def is_manager():
    return 'username' in session and session.get('role') == 'Manager'

# Kiểm tra quyền Employee
def is_employee():
    return 'username' in session and session.get('role') == 'Employee'

# Trang chủ - Chuyển hướng đến đăng nhập nếu chưa xác thực
@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('materials'))

# Trang đăng nhập
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        if conn is None:
            return redirect(url_for('login'))
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE username = %s AND password = %s', (username, password))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if user:
            session['username'] = username
            session['role'] = user['role']
            session['user_id'] = user['id']  # Lưu user_id vào session
            session['employee_id'] = user['employee_id']  # Lưu employee_id vào session
            return redirect(url_for('materials'))
        else:
            flash('Tên người dùng hoặc mật khẩu không đúng', 'error')
    return render_template('login.html')

# Trang đăng xuất
@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    session.pop('user_id', None)
    session.pop('employee_id', None)  # Xóa employee_id khỏi session
    return redirect(url_for('login'))

# Quản lý vật tư
@app.route('/materials', methods=['GET', 'POST'])
def materials():
    if 'username' not in session:
        return redirect(url_for('login'))
    if not (is_manager() or is_employee()):
        return render_template('no_permission.html', message="Bạn không có quyền truy cập")
    conn = get_db_connection()
    if conn is None:
        return redirect(url_for('materials'))
    cursor = conn.cursor(dictionary=True)

    # Lấy các tham số tìm kiếm
    search_code = request.args.get('search_code', '')
    search_name = request.args.get('search_name', '')
    min_purchase_price = request.args.get('min_purchase_price', '')
    max_purchase_price = request.args.get('max_purchase_price', '')
    min_sale_price = request.args.get('min_sale_price', '')
    max_sale_price = request.args.get('max_sale_price', '')
    min_stock = request.args.get('min_stock', '')
    max_stock = request.args.get('max_stock', '')
    search_status = request.args.get('search_status', '')

    # Xây dựng câu truy vấn SQL động
    query = 'SELECT * FROM materials WHERE 1=1'
    params = []

    if search_code:
        query += ' AND code LIKE %s'
        params.append(f'%{search_code}%')
    
    if search_name:
        query += ' AND name LIKE %s'
        params.append(f'%{search_name}%')
    
    if min_purchase_price:
        query += ' AND purchase_price >= %s'
        params.append(float(min_purchase_price))
    
    if max_purchase_price:
        query += ' AND purchase_price <= %s'
        params.append(float(max_purchase_price))
    
    if min_sale_price:
        query += ' AND sale_price >= %s'
        params.append(float(min_sale_price))
    
    if max_sale_price:
        query += ' AND sale_price <= %s'
        params.append(float(max_sale_price))
    
    if min_stock:
        query += ' AND stock >= %s'
        params.append(int(min_stock))
    
    if max_stock:
        query += ' AND stock <= %s'
        params.append(int(max_stock))
    
    if search_status:
        query += ' AND status = %s'
        params.append(search_status)

    # Thực thi truy vấn
    cursor.execute(query, tuple(params))
    materials = cursor.fetchall()
    
    cursor.close()
    conn.close()
    return render_template('materials.html', materials=materials)

# Thêm vật tư
@app.route('/add_material', methods=['GET', 'POST'])
def add_material():
    if 'username' not in session:
        return redirect(url_for('login'))
    if not (is_manager() or is_employee()):
        return render_template('no_permission.html', message="Bạn không có quyền thực hiện hành động này")
    
    if request.method == 'GET':
        return render_template('add_material.html')
        
    code = request.form['code']
    name = request.form['name']
    unit = request.form['unit']
    purchase_price = float(request.form['purchase_price'])
    sale_price = float(request.form['sale_price'])
    stock = int(request.form['stock'])
    supplier_name = request.form.get('supplier_name', '')
    supplier_phone = request.form.get('supplier_phone', '')
    status = 'Còn hàng' if stock > 0 else 'Hết hàng'

    conn = get_db_connection()
    if conn is None:
        return redirect(url_for('materials'))
    cursor = conn.cursor()

    try:
        # Thêm vật tư vào bảng materials
        cursor.execute('''
            INSERT INTO materials (code, name, unit, purchase_price, sale_price, stock, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (code, name, unit, purchase_price, sale_price, stock, status))
        conn.commit()

        # Lấy ID của vật tư vừa thêm
        cursor.execute('SELECT LAST_INSERT_ID() AS id')
        material_id = cursor.fetchone()[0]

        # Nếu stock > 0, ghi lại giao dịch nhập hàng vào bảng transactions với employee_id và thông tin nhà cung cấp
        employee_id = session.get('employee_id')
        if stock > 0 and employee_id:
            cursor.execute('''
                INSERT INTO transactions (material_id, type, quantity, date, employee_id, supplier_name, supplier_phone)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (material_id, 'purchase', stock, datetime.now(), employee_id, supplier_name, supplier_phone))
            conn.commit()

        flash('Thêm vật tư và giao dịch nhập hàng thành công', 'success')
    except mysql.connector.Error as err:
        conn.rollback()
        flash(f'Lỗi khi thêm vật tư: {err}', 'error')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('materials'))

# Sửa vật tư
@app.route('/edit_material/<int:id>', methods=['GET', 'POST'])
def edit_material(id):
    if 'username' not in session:
        return redirect(url_for('login'))
    if not is_manager():
        return render_template('no_permission.html', message="Bạn không có quyền thực hiện hành động này")
    conn = get_db_connection()
    if conn is None:
        return redirect(url_for('materials'))
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        code = request.form['code']
        name = request.form['name']
        unit = request.form['unit']
        purchase_price = float(request.form['purchase_price'])
        sale_price = float(request.form['sale_price'])
        stock = int(request.form['stock'])
        status = 'Còn hàng' if stock > 0 else 'Hết hàng'

        cursor.execute('''
            UPDATE materials 
            SET code=%s, name=%s, unit=%s, purchase_price=%s, sale_price=%s, stock=%s, status=%s 
            WHERE id=%s
        ''', (code, name, unit, purchase_price, sale_price, stock, status, id))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('materials'))

    cursor.execute('SELECT * FROM materials WHERE id=%s', (id,))
    material = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('edit_material.html', material=material)

# Xóa vật tư
@app.route('/delete_material/<int:id>')
def delete_material(id):
    if 'username' not in session:
        return redirect(url_for('login'))
    if not is_manager():
        return render_template('no_permission.html', message="Bạn không có quyền thực hiện hành động này")
    conn = get_db_connection()
    if conn is None:
        return redirect(url_for('materials'))
    cursor = conn.cursor()
    
    # Xóa tất cả giao dịch liên quan đến vật tư này
    cursor.execute('DELETE FROM transactions WHERE material_id=%s', (id,))
    
    # Sau đó xóa vật tư
    cursor.execute('DELETE FROM materials WHERE id=%s', (id,))
    
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('materials'))

# Nhập hàng
@app.route('/purchase', methods=['GET', 'POST'])
def purchase():
    if 'username' not in session:
        return redirect(url_for('login'))
    if not (is_manager() or is_employee()):
        return render_template('no_permission.html', message="Bạn không có quyền thực hiện hành động này")
    conn = get_db_connection()
    if conn is None:
        return redirect(url_for('materials'))
    cursor = conn.cursor(dictionary=True)

    # Lấy danh sách vật tư kèm thông tin nhà cung cấp gần nhất
    cursor.execute('''
        SELECT m.*, 
               t.supplier_name as last_supplier_name,
               t.supplier_phone as last_supplier_phone
        FROM materials m
        LEFT JOIN (
            SELECT material_id, supplier_name, supplier_phone,
                   ROW_NUMBER() OVER (PARTITION BY material_id ORDER BY date DESC) as rn
            FROM transactions
            WHERE type = 'purchase' AND supplier_name IS NOT NULL
        ) t ON m.id = t.material_id AND t.rn = 1
    ''')
    materials = cursor.fetchall()

    if request.method == 'POST':
        material_id = int(request.form['material_id'])
        quantity = int(request.form['quantity'])
        supplier_name = request.form.get('supplier_name', '')
        supplier_phone = request.form.get('supplier_phone', '')
        
        # Cập nhật tồn kho
        cursor.execute('SELECT stock FROM materials WHERE id=%s', (material_id,))
        current_stock = cursor.fetchone()['stock']
        new_stock = current_stock + quantity
        status = 'Còn hàng' if new_stock > 0 else 'Hết hàng'
        
        cursor.execute('UPDATE materials SET stock=%s, status=%s WHERE id=%s', 
                       (new_stock, status, material_id))
        
        # Ghi lại giao dịch với employee_id và thông tin người cung cấp
        employee_id = session.get('employee_id')
        if employee_id:
            cursor.execute('''
                INSERT INTO transactions (material_id, type, quantity, date, employee_id, supplier_name, supplier_phone)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (material_id, 'purchase', quantity, datetime.now(), employee_id, supplier_name, supplier_phone))
            conn.commit()

        cursor.close()
        conn.close()
        return redirect(url_for('materials'))

    cursor.close()
    conn.close()
    return render_template('purchase.html', materials=materials)

# Bán hàng
@app.route('/sell', methods=['GET', 'POST'])
def sell():
    if 'username' not in session:
        return redirect(url_for('login'))
    if not (is_manager() or is_employee()):
        return render_template('no_permission.html', message="Bạn không có quyền thực hiện hành động này")
    conn = get_db_connection()
    if conn is None:
        return redirect(url_for('materials'))
    cursor = conn.cursor(dictionary=True)

    # Lấy danh sách vật tư
    cursor.execute('SELECT * FROM materials')
    materials = cursor.fetchall()

    if request.method == 'POST':
        material_id = int(request.form['material_id'])
        quantity = int(request.form['quantity'])
        customer_name = request.form.get('customer_name', '')
        customer_phone = request.form.get('customer_phone', '')
        
        # Cập nhật tồn kho
        cursor.execute('SELECT stock FROM materials WHERE id=%s', (material_id,))
        current_stock = cursor.fetchone()['stock']
        if current_stock >= quantity:
            new_stock = current_stock - quantity
            status = 'Còn hàng' if new_stock > 0 else 'Hết hàng'
            
            cursor.execute('UPDATE materials SET stock=%s, status=%s WHERE id=%s', 
                           (new_stock, status, material_id))
            
            # Ghi lại giao dịch với employee_id và thông tin khách hàng
            employee_id = session.get('employee_id')
            if employee_id:
                cursor.execute('''
                    INSERT INTO transactions (material_id, type, quantity, date, employee_id, customer_name, customer_phone)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''', (material_id, 'sale', quantity, datetime.now(), employee_id, customer_name, customer_phone))
                conn.commit()
        else:
            flash('Không đủ hàng để bán', 'error')
        cursor.close()
        conn.close()
        return redirect(url_for('materials'))

    cursor.close()
    conn.close()
    return render_template('sell.html', materials=materials)

# Thống kê
@app.route('/statistics')
def statistics():
    if 'username' not in session:
        return redirect(url_for('login'))
    if not is_manager():
        return render_template('no_permission.html', message="Bạn không có quyền thực hiện hành động này")
    conn = get_db_connection()
    if conn is None:
        return redirect(url_for('materials'))
    cursor = conn.cursor(dictionary=True)

    # Biểu đồ mức tồn kho
    cursor.execute('SELECT name, stock FROM materials')
    materials = cursor.fetchall()
    names = [m['name'] for m in materials]
    stocks = [m['stock'] for m in materials]

    plt.figure(figsize=(10, 6))
    plt.bar(names, stocks, color='skyblue')
    plt.title('MỨC TỒN KHO CỦA VẬT TƯ',fontdict={'family': 'Times New Roman', 'size': 16, 'weight': 'bold'})
    plt.xlabel('Vật tư',fontdict={'family': 'Times New Roman', 'size': 16, 'weight': 'bold'})
    plt.ylabel('Tồn kho',fontdict={'family': 'Times New Roman', 'size': 16, 'weight': 'bold'})
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig('static/charts/stock_levels.png')
    plt.close()

    # Biểu đồ vật tư bán chạy nhất (dạng thanh ngang)
    cursor.execute('''
        SELECT m.name, SUM(t.quantity) as total_sold
        FROM transactions t
        JOIN materials m ON t.material_id = m.id
        WHERE t.type = 'sale'
        GROUP BY m.name
        ORDER BY total_sold DESC
        LIMIT 10
    ''')
    sales_data = cursor.fetchall()
    
    if sales_data:
        names = [item['name'] for item in sales_data]
        quantities = [item['total_sold'] for item in sales_data]

        plt.figure(figsize=(10, 6))
        bars = plt.barh(names, quantities, color='#28a745')
        plt.title('TOP 10 VẬT TƯ BÁN CHẠY NHẤT', fontdict={'family': 'Times New Roman', 'size': 16, 'weight': 'bold'})
        plt.xlabel('Số lượng đã bán', fontdict={'family': 'Times New Roman', 'size': 12})
        
        # Thêm giá trị số lượng vào cuối mỗi thanh
        for i, bar in enumerate(bars):
            width = bar.get_width()
            plt.text(width, bar.get_y() + bar.get_height()/2, 
                    f'{int(width):,}', 
                    va='center', 
                    fontdict={'family': 'Times New Roman', 'size': 10})

        plt.gca().invert_yaxis()  # Đảo ngược trục y để item cao nhất ở trên cùng
        plt.tight_layout()
        plt.savefig('static/charts/best_selling.png')
        plt.close()

    # Biểu đồ tròn phân phối tồn kho
    total_stock = sum(stocks)
    if total_stock > 0:
        percentages = [(stock / total_stock) * 100 for stock in stocks]
        colors = ["#fc3b3b", "#459ff8", "#47ff47", "#ff962d", "#ff41a0"]
        plt.figure(figsize=(8, 8))
        wedges, texts, autotexts = plt.pie(
            percentages, 
            colors=colors, 
            startangle=90, 
            autopct='%1.1f%%', 
            wedgeprops={'edgecolor': 'white'},
            textprops={'fontsize': 12}
        )
        plt.legend(
            wedges, 
            names, 
            title="Vật Tư", 
            loc="center left", 
            bbox_to_anchor=(1, 0, 0.5, 1)
        )
        plt.title('BIỂU ĐỒ PHÂN PHỐI TỒN KHO CỦA VẬT TƯ', loc='center', pad=5,fontdict={'family': 'Times New Roman', 'size': 16, 'weight': 'bold'})
        plt.axis('equal')
        plt.subplots_adjust(top=0.9)
        plt.savefig('static/charts/stock_distribution.png', bbox_inches='tight')
        plt.close()

    # Biểu đồ cột: Thống kê nhập hàng và bán hàng theo ngày
    cursor.execute('SELECT type, quantity, date FROM transactions ORDER BY date')
    transactions = cursor.fetchall()

    # Thêm biểu đồ đường: Doanh thu bán hàng theo ngày
    cursor.execute('''
        SELECT DATE(t.date) as sale_date, SUM(t.quantity * m.sale_price) as daily_revenue
        FROM transactions t
        JOIN materials m ON t.material_id = m.id
        WHERE t.type = 'sale'
        GROUP BY DATE(t.date)
        ORDER BY sale_date
    ''')
    revenue_data = cursor.fetchall()
    
    if revenue_data:
        sale_dates = [row['sale_date'].strftime('%Y-%m-%d') for row in revenue_data]
        daily_revenues = [float(row['daily_revenue']) for row in revenue_data]

        plt.figure(figsize=(12, 6))
        plt.plot(sale_dates, daily_revenues, marker='o', linestyle='-', linewidth=2, color='#198754')
        plt.fill_between(sale_dates, daily_revenues, alpha=0.2, color='#198754')
        
        plt.title('DOANH THU BÁN HÀNG THEO NGÀY', fontdict={'family': 'Times New Roman', 'size': 16, 'weight': 'bold'})
        plt.xlabel('Ngày', fontdict={'family': 'Times New Roman', 'size': 12})
        plt.ylabel('Doanh thu (VNĐ)', fontdict={'family': 'Times New Roman', 'size': 12})
        
        # Xoay nhãn trục x để dễ đọc
        plt.xticks(rotation=45, ha='right')
        
        # Thêm lưới để dễ theo dõi
        plt.grid(True, linestyle='--', alpha=0.7)
        
        # Format giá trị trục y thành định dạng tiền tệ
        plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: format(int(x), ',')))
        
        plt.tight_layout()
        plt.savefig('static/charts/daily_revenue.png')
        plt.close()

    dates = []
    purchases = []
    sales = []
    current_date = None
    purchase_sum = 0
    sale_sum = 0

    for t in transactions:
        date = t['date'].strftime('%Y-%m-%d')
        if date != current_date:
            if current_date:
                dates.append(current_date)
                purchases.append(purchase_sum)
                sales.append(sale_sum)
            current_date = date
            purchase_sum = 0
            sale_sum = 0
        if t['type'] == 'purchase':
            purchase_sum += t['quantity']
        else:
            sale_sum += t['quantity']
    if current_date:
        dates.append(current_date)
        purchases.append(purchase_sum)
        sales.append(sale_sum)

    # Tạo biểu đồ cột
    plt.figure(figsize=(10, 6))
    x = range(len(dates))
    plt.bar(x, purchases, width=0.4, label='Nhập Hàng', color='#28a745', align='center')
    plt.bar([i + 0.4 for i in x], sales, width=0.4, label='Bán Hàng', color='#ff9800', align='center')
    plt.xlabel('Ngày',fontdict={'family': 'Times New Roman', 'size': 16, 'weight': 'bold'})
    plt.ylabel('Số lượng',fontdict={'family': 'Times New Roman', 'size': 16, 'weight': 'bold'})
    plt.title('THỐNG KÊ NHẬP HÀNG VÀ BÁN HÀNG THEO NGÀY',fontdict={'family': 'Times New Roman', 'size': 16, 'weight': 'bold'})
    plt.xticks(x, dates, rotation=45)
    plt.legend()
    plt.tight_layout()
    plt.savefig('static/charts/purchase_sale_by_day.png')
    plt.close()

    # Tính tổng chi phí nhập hàng
    cursor.execute('''
        SELECT t.quantity, m.purchase_price
        FROM transactions t
        JOIN materials m ON t.material_id = m.id
        WHERE t.type = 'purchase'
    ''')
    purchases = cursor.fetchall()
    total_cost = sum(p['quantity'] * p['purchase_price'] for p in purchases)

    # Tính tổng doanh thu bán hàng
    cursor.execute('''
        SELECT t.quantity, m.sale_price
        FROM transactions t
        JOIN materials m ON t.material_id = m.id
        WHERE t.type = 'sale'
    ''')
    sales = cursor.fetchall()
    total_revenue = sum(s['quantity'] * s['sale_price'] for s in sales)

    cursor.close()
    conn.close()
    return render_template('statistics.html', total_cost=total_cost, total_revenue=total_revenue)

# Danh sách đơn hàng
@app.route('/orders')
def orders():
    if 'username' not in session:
        return redirect(url_for('login'))
    if not (is_manager() or is_employee()):
        return render_template('no_permission.html', message="Bạn không có quyền truy cập")
    conn = get_db_connection()
    if conn is None:
        return redirect(url_for('materials'))
    cursor = conn.cursor(dictionary=True)

    # Lấy danh sách mã vật tư cho dropdown
    cursor.execute('SELECT DISTINCT code FROM materials ORDER BY code')
    material_codes = [row['code'] for row in cursor.fetchall()]

    # Lấy tham số tìm kiếm từ query string
    search_id = request.args.get('search_id', '')
    search_name = request.args.get('search_name', '')
    search_code = request.args.get('search_code', '')
    search_type = request.args.get('search_type', '')
    search_employee_id = request.args.get('search_employee_id', '')
    search_date_from = request.args.get('search_date_from', '')
    search_date_to = request.args.get('search_date_to', '')
    search_value_min = request.args.get('search_value_min', '')
    search_value_max = request.args.get('search_value_max', '')

    # Truy vấn cơ sở dữ liệu với điều kiện tìm kiếm
    query = '''
        SELECT t.id, t.date, t.type, m.name, m.code, t.quantity, 
               t.employee_id, 
               CASE t.type 
                   WHEN 'purchase' THEN m.purchase_price * t.quantity 
                   WHEN 'sale' THEN m.sale_price * t.quantity 
               END AS value
        FROM transactions t
        JOIN materials m ON t.material_id = m.id
        WHERE 1=1
    '''
    params = []

    if search_id:
        query += ' AND t.id = %s'
        params.append(search_id)
    if search_name:
        query += ' AND m.name LIKE %s'
        params.append(f'%{search_name}%')
    if search_code:
        query += ' AND m.code = %s'
        params.append(search_code)
    if search_type:
        query += ' AND t.type = %s'
        params.append(search_type)
    if search_employee_id:
        query += ' AND t.employee_id = %s'
        params.append(search_employee_id)
    if search_date_from:
        query += ' AND DATE(t.date) >= %s'
        params.append(search_date_from)
    if search_date_to:
        query += ' AND DATE(t.date) <= %s'
        params.append(search_date_to)
    if search_value_min:
        query += ' AND (CASE t.type WHEN "purchase" THEN m.purchase_price * t.quantity WHEN "sale" THEN m.sale_price * t.quantity END) >= %s'
        params.append(float(search_value_min))
    if search_value_max:
        query += ' AND (CASE t.type WHEN "purchase" THEN m.purchase_price * t.quantity WHEN "sale" THEN m.sale_price * t.quantity END) <= %s'
        params.append(float(search_value_max))

    query += ' ORDER BY t.date DESC'
    cursor.execute(query, params)
    transactions = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template('orders.html', 
                         transactions=transactions,
                         material_codes=material_codes,
                         search_id=search_id,
                         search_name=search_name,
                         search_code=search_code,
                         search_type=search_type,
                         search_employee_id=search_employee_id,
                         search_date_from=search_date_from,
                         search_date_to=search_date_to,
                         search_value_min=search_value_min,
                         search_value_max=search_value_max)

# Xem chi tiết đơn hàng
@app.route('/order_detail/<int:order_id>')
def order_detail(order_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    if not (is_manager() or is_employee()):
        return render_template('no_permission.html', message="Bạn không có quyền truy cập")
    conn = get_db_connection()
    if conn is None:
        return redirect(url_for('materials'))
    cursor = conn.cursor(dictionary=True)

    cursor.execute('''
        SELECT t.id, t.date, t.type, m.name, m.code, t.quantity, 
               t.employee_id, 
               CASE t.type 
                   WHEN 'purchase' THEN m.purchase_price * t.quantity 
                   WHEN 'sale' THEN m.sale_price * t.quantity 
               END AS value,
               t.supplier_name, t.supplier_phone, t.customer_name, t.customer_phone
        FROM transactions t
        JOIN materials m ON t.material_id = m.id
        WHERE t.id = %s
    ''', (order_id,))
    transaction = cursor.fetchone()

    cursor.close()
    conn.close()
    return render_template('order_detail.html', transaction=transaction)

# Đổi mật khẩu
@app.route('/change_password/<int:user_id>', methods=['GET', 'POST'])
def change_password(user_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    if not is_manager():
        return render_template('no_permission.html', message="Bạn không có quyền thực hiện hành động này")
    conn = get_db_connection()
    if conn is None:
        return redirect(url_for('permissions'))
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        new_password = request.form['new_password']
        try:
            cursor.execute('UPDATE users SET password = %s WHERE id = %s', (new_password, user_id))
            conn.commit()
            flash('Đổi mật khẩu thành công', 'success')
            return redirect(url_for('permissions'))
        except mysql.connector.Error as err:
            flash(f'Lỗi khi đổi mật khẩu: {err}', 'error')
            conn.rollback()

    # Lấy thông tin người dùng để hiển thị
    cursor.execute('SELECT username FROM users WHERE id = %s', (user_id,))
    user = cursor.fetchone()
    if not user:
        flash('User does not exist', 'error')
        return redirect(url_for('permissions'))

    cursor.close()
    conn.close()
    return render_template('change_password.html', user_id=user_id, username=user['username'])

# Quản lý phân quyền
@app.route('/permissions', methods=['GET', 'POST'])
def permissions():
    if 'username' not in session:
        return redirect(url_for('login'))
    if not is_manager():
        return render_template('no_permission.html', message="Bạn không có quyền thực hiện hành động này")
    conn = get_db_connection()
    if conn is None:
        return redirect(url_for('permissions'))
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            username = request.form['username']
            password = request.form['password']
            role = request.form['role']
            employee_id = request.form.get('employee_id')
            full_name = request.form.get('full_name')
            phone_number = request.form.get('phone_number')
            try:
                if not employee_id and role == 'Employee':
                    flash('Vui lòng nhập ID Nhân Viên cho vai trò Employee', 'error')
                else:
                    cursor.execute('''
                        INSERT INTO users (username, password, role, employee_id, full_name, phone_number)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    ''', (username, password, role, employee_id, full_name, phone_number))
                    conn.commit()
                    flash('Thêm người dùng thành công', 'success')
            except mysql.connector.Error as err:
                flash(f'Lỗi khi thêm người dùng: {err}', 'error')
        elif action == 'update':
            user_id = request.form['user_id']
            role = request.form['role']
            employee_id = request.form.get('employee_id')
            full_name = request.form.get('full_name')
            phone_number = request.form.get('phone_number')
            try:
                # Lấy giá trị employee_id hiện tại nếu không có giá trị mới
                cursor.execute('SELECT employee_id FROM users WHERE id = %s', (user_id,))
                current_employee_id = cursor.fetchone()['employee_id']
                if not employee_id and role == 'Employee':
                    employee_id = current_employee_id if current_employee_id else None
                    if not employee_id:
                        flash('Vui lòng nhập ID Nhân Viên cho vai trò Employee', 'error')
                        return redirect(url_for('permissions'))
                cursor.execute('''
                    UPDATE users SET role = %s, employee_id = %s, full_name = %s, phone_number = %s WHERE id = %s
                ''', (role, employee_id, full_name, phone_number, user_id))
                conn.commit()
                flash('Cập nhật vai trò và thông tin thành công', 'success')
            except mysql.connector.Error as err:
                flash(f'Lỗi khi cập nhật vai trò: {err}', 'error')
                conn.rollback()
        elif action == 'delete':
            try:
                user_id = int(request.form['user_id'])
                # Kiểm tra nếu người dùng tồn tại
                cursor.execute('SELECT id, username FROM users WHERE id = %s', (user_id,))
                user = cursor.fetchone()
                if not user:
                    flash('Người dùng không tồn tại', 'error')
                else:
                    # Kiểm tra nếu người dùng đang cố xóa chính mình
                    current_user_id = session.get('user_id')
                    if current_user_id is None:
                        flash('Phiên đăng nhập không hợp lệ, vui lòng đăng nhập lại', 'error')
                        return redirect(url_for('logout'))
                    if user_id == current_user_id:
                        flash('Không thể xóa người dùng đang đăng nhập', 'error')
                    else:
                        cursor.execute('DELETE FROM users WHERE id = %s', (user_id,))
                        conn.commit()
                        flash('Xóa người dùng thành công', 'success')
            except ValueError:
                flash('ID người dùng không hợp lệ', 'error')
            except mysql.connector.Error as err:
                flash(f'Lỗi khi xóa người dùng: {err}', 'error')

    cursor.execute('SELECT * FROM users')
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('permissions.html', users=users)

@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    if not is_manager():
        return render_template('no_permission.html', message="Bạn không có quyền thực hiện hành động này")

    conn = get_db_connection()
    if conn is None:
        return redirect(url_for('permissions'))
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        role = request.form['role']
        employee_id = request.form['employee_id'] if role == 'Employee' else None
        full_name = request.form['full_name']
        phone_number = request.form['phone_number']

        try:
            cursor.execute('''
                UPDATE users 
                SET role = %s, employee_id = %s, full_name = %s, phone_number = %s 
                WHERE id = %s
            ''', (role, employee_id, full_name, phone_number, user_id))
            conn.commit()
            flash('Cập nhật thông tin người dùng thành công', 'success')
            return redirect(url_for('permissions'))
        except mysql.connector.Error as err:
            flash(f'Lỗi: {err}', 'error')
            conn.rollback()

    # Lấy thông tin người dùng hiện tại
    cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if user is None:
        flash('Không tìm thấy người dùng', 'error')
        return redirect(url_for('permissions'))

    return render_template('edit_user.html', user=user)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)