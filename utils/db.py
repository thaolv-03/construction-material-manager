import os
import mysql.connector
from mysql.connector import pooling
from dotenv import load_dotenv
from flask import current_app

# Tải biến môi trường từ file .env
load_dotenv()

# Cấu hình MySQL với biến môi trường
db_config = {
    'host': os.getenv("MYSQL_HOST"),
    'user': os.getenv("MYSQL_USER"),
    'password': os.getenv("MYSQL_PASSWORD"),
    'port': int(os.getenv("MYSQL_PORT", 3306)),
    'database': os.getenv("MYSQL_DATABASE"),
    'raise_on_warnings': False,
    'ssl_ca': None,
    'ssl_cert': None,
    'ssl_key': None,
    'ssl_verify_cert': False
}

# Tạo connection pool cho MySQL
connection_pool = mysql.connector.pooling.MySQLConnectionPool(
    pool_name="mypool",
    pool_size=5,
    pool_reset_session=True,
    **db_config
)

def get_db_connection():
    try:
        conn = connection_pool.get_connection()
        if conn.is_connected():
            return conn
        else:
            raise Exception("Không thể kết nối đến cơ sở dữ liệu")
    except Exception as e:
        current_app.logger.error(f"Lỗi kết nối cơ sở dữ liệu: {str(e)}")
        return None

def init_db():
    conn = get_db_connection()
    if conn is None:
        return
    cursor = conn.cursor()
    
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
                type VARCHAR(50),
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