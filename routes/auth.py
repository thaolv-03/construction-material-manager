from flask import render_template, request, redirect, url_for, session, flash
from utils.db import get_db_connection
from utils.auth import is_manager, is_employee
import mysql.connector

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
            session['user_id'] = user['id']
            session['employee_id'] = user['employee_id']
            return redirect(url_for('materials'))
        else:
            flash('Tên người dùng hoặc mật khẩu không đúng', 'error')
    return render_template('login.html')

def logout():
    session.pop('username', None)
    session.pop('role', None)
    session.pop('user_id', None)
    session.pop('employee_id', None)
    return redirect(url_for('login'))

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

    cursor.execute('SELECT username FROM users WHERE id = %s', (user_id,))
    user = cursor.fetchone()
    if not user:
        flash('User does not exist', 'error')
        return redirect(url_for('permissions'))

    cursor.close()
    conn.close()
    return render_template('change_password.html', user_id=user_id, username=user['username']) 