from flask import render_template, request, redirect, url_for, session, flash
from utils.db import get_db_connection
from utils.auth import is_manager, is_employee
from datetime import datetime
import mysql.connector

def materials():
    if 'username' not in session:
        return redirect(url_for('login'))
    if not (is_manager() or is_employee()):
        return render_template('no_permission.html', message="Bạn không có quyền truy cập")
    conn = get_db_connection()
    if conn is None:
        return redirect(url_for('materials'))
    cursor = conn.cursor(dictionary=True)

    search_code = request.args.get('search_code', '')
    search_name = request.args.get('search_name', '')
    min_purchase_price = request.args.get('min_purchase_price', '')
    max_purchase_price = request.args.get('max_purchase_price', '')
    min_sale_price = request.args.get('min_sale_price', '')
    max_sale_price = request.args.get('max_sale_price', '')
    min_stock = request.args.get('min_stock', '')
    max_stock = request.args.get('max_stock', '')
    search_status = request.args.get('search_status', '')

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

    cursor.execute(query, tuple(params))
    materials = cursor.fetchall()
    
    cursor.close()
    conn.close()
    return render_template('materials.html', materials=materials)

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
        cursor.execute('''
            INSERT INTO materials (code, name, unit, purchase_price, sale_price, stock, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (code, name, unit, purchase_price, sale_price, stock, status))
        conn.commit()

        cursor.execute('SELECT LAST_INSERT_ID() AS id')
        material_id = cursor.fetchone()[0]

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
        status = 'Còn hàng' if stock > 0 else 'Hết hàng'

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

def delete_material(id):
    if 'username' not in session:
        return redirect(url_for('login'))
    if not is_manager():
        return render_template('no_permission.html', message="Bạn không có quyền thực hiện hành động này")
    conn = get_db_connection()
    if conn is None:
        return redirect(url_for('materials'))
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM transactions WHERE material_id=%s', (id,))
    cursor.execute('DELETE FROM materials WHERE id=%s', (id,))
    
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('materials'))
