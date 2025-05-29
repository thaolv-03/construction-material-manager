from flask import render_template, request, redirect, url_for, session, flash
from utils.db import get_db_connection
from utils.auth import is_manager
import mysql.connector

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
        elif action == 'delete':
            try:
                user_id = int(request.form['user_id'])
                cursor.execute('SELECT id, username FROM users WHERE id = %s', (user_id,))
                user = cursor.fetchone()
                if not user:
                    flash('Người dùng không tồn tại', 'error')
                else:
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
        # Lấy employee_id từ form và từ database
        new_employee_id = request.form.get('employee_id')
        cursor.execute('SELECT employee_id FROM users WHERE id = %s', (user_id,))
        current_user = cursor.fetchone()
        current_employee_id = current_user['employee_id'] if current_user else None

        # Xử lý employee_id
        if role == 'Employee':
            # Nếu là Employee, bắt buộc phải có employee_id
            if new_employee_id:
                employee_id = new_employee_id
            elif current_employee_id:
                employee_id = current_employee_id
            else:
                flash('Vui lòng nhập ID Nhân Viên cho vai trò Employee', 'error')
                cursor.close()
                conn.close()
                return redirect(url_for('edit_user', user_id=user_id))
        else:
            # Nếu không phải Employee, sử dụng employee_id mới nếu có, không thì giữ cái cũ
            employee_id = new_employee_id if new_employee_id else current_employee_id

        full_name = request.form['full_name']
        phone_number = request.form.get('phone_number')

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

    cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if user is None:
        flash('Không tìm thấy người dùng', 'error')
        return redirect(url_for('permissions'))

    return render_template('edit_user.html', user=user)
