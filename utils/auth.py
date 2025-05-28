from flask import session

def is_manager():
    return 'username' in session and session.get('role') == 'Manager'

def is_employee():
    return 'username' in session and session.get('role') == 'Employee' 