from flask import render_template, redirect, url_for, session
from utils.db import get_db_connection
from utils.auth import is_manager
import matplotlib
matplotlib.use('Agg')  # Sử dụng backend Agg cho môi trường không có GUI
import matplotlib.pyplot as plt

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
    plt.title('MỨC TỒN KHO CỦA VẬT TƯ',fontdict={'family': 'Times New Roman', 'size': 16, 'weight': 'bold'})
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
        plt.title('BIỂU ĐỒ PHÂN PHỐI TỒN KHO CỦA VẬT TƯ', loc='center', pad=5,fontdict={'family': 'Times New Roman', 'size': 16, 'weight': 'bold'})
        plt.axis('equal')
        plt.subplots_adjust(top=0.9)
        plt.savefig('static/charts/stock_distribution.png', bbox_inches='tight')
        plt.close()

    # Biểu đồ đường: Doanh thu bán hàng theo ngày
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
        
        plt.xticks(rotation=45, ha='right')
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: format(int(x), ',')))
        
        plt.tight_layout()
        plt.savefig('static/charts/daily_revenue.png')
        plt.close()

    # Biểu đồ cột: Thống kê nhập hàng và bán hàng theo ngày
    cursor.execute('SELECT type, quantity, date FROM transactions ORDER BY date')
    transactions = cursor.fetchall()

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
    plt.xlabel('Ngày',fontdict={'family': 'Times New Roman', 'size': 16, 'weight': 'bold'})
    plt.ylabel('Số lượng',fontdict={'family': 'Times New Roman', 'size': 16, 'weight': 'bold'})
    plt.title('THỐNG KÊ NHẬP HÀNG VÀ BÁN HÀNG THEO NGÀY',fontdict={'family': 'Times New Roman', 'size': 16, 'weight': 'bold'})
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
