from flask import render_template, request, redirect, url_for, session, flash
from utils.db import get_db_connection
from utils.auth import is_manager, is_employee
from datetime import datetime
import mysql.connector

def purchase():
    if 'username' not in session:
        return redirect(url_for('login'))
    if not (is_manager() or is_employee()):
        return render_template('no_permission.html', message="Bạn không có quyền thực hiện hành động này")
    conn = get_db_connection()
    if conn is None:
        return redirect(url_for('materials'))
    cursor = conn.cursor(dictionary=True)

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
        
        cursor.execute('SELECT stock FROM materials WHERE id=%s', (material_id,))
        current_stock = cursor.fetchone()['stock']
        new_stock = current_stock + quantity
        status = 'Còn hàng' if new_stock > 0 else 'Hết hàng'
        
        cursor.execute('UPDATE materials SET stock=%s, status=%s WHERE id=%s', 
                       (new_stock, status, material_id))
        
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

def sell():
    if 'username' not in session:
        return redirect(url_for('login'))
    if not (is_manager() or is_employee()):
        return render_template('no_permission.html', message="Bạn không có quyền thực hiện hành động này")
    conn = get_db_connection()
    if conn is None:
        return redirect(url_for('materials'))
    cursor = conn.cursor(dictionary=True)

    cursor.execute('SELECT * FROM materials')
    materials = cursor.fetchall()

    if request.method == 'POST':
        material_id = int(request.form['material_id'])
        quantity = int(request.form['quantity'])
        customer_name = request.form.get('customer_name', '')
        customer_phone = request.form.get('customer_phone', '')
        
        cursor.execute('SELECT stock FROM materials WHERE id=%s', (material_id,))
        current_stock = cursor.fetchone()['stock']
        if current_stock >= quantity:
            new_stock = current_stock - quantity
            status = 'Còn hàng' if new_stock > 0 else 'Hết hàng'
            
            cursor.execute('UPDATE materials SET stock=%s, status=%s WHERE id=%s', 
                           (new_stock, status, material_id))
            
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

def orders():
    if 'username' not in session:
        return redirect(url_for('login'))
    if not (is_manager() or is_employee()):
        return render_template('no_permission.html', message="Bạn không có quyền truy cập")
    conn = get_db_connection()
    if conn is None:
        return redirect(url_for('materials'))
    cursor = conn.cursor(dictionary=True)

    cursor.execute('SELECT DISTINCT code FROM materials ORDER BY code')
    material_codes = [row['code'] for row in cursor.fetchall()]

    search_id = request.args.get('search_id', '')
    search_name = request.args.get('search_name', '')
    search_code = request.args.get('search_code', '')
    search_type = request.args.get('search_type', '')
    search_employee_id = request.args.get('search_employee_id', '')
    search_date_from = request.args.get('search_date_from', '')
    search_date_to = request.args.get('search_date_to', '')
    search_value_min = request.args.get('search_value_min', '')
    search_value_max = request.args.get('search_value_max', '')

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
