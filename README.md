# Hệ Thống Quản Lý Vật Tư Cửa Hàng Vật Liệu Xây Dựng

## 1. Tổng quan dự án
**Mục đích**: Hệ thống được thiết kế để quản lý vật tư cho cửa hàng vật liệu xây dựng, bao gồm các chức năng như quản lý vật tư, giao dịch, thống kê, và phân quyền người dùng.  

**Công nghệ sử dụng**:
- **Python Flask**: Framework web để xây dựng ứng dụng.
- **MySQL**: Cơ sở dữ liệu để lưu trữ thông tin vật tư, giao dịch, và người dùng.
- **Python 3.8+** và **MySQL 5.7+** là yêu cầu tối thiểu.
- Các thư viện Python cần thiết được liệt kê trong `requirements.txt`.

## 2. Tính năng chính
### Quản lý Vật Tư
- Thêm, sửa, xóa vật tư.
- Tìm kiếm vật tư theo nhiều tiêu chí (tên, loại, giá, v.v.).
- Theo dõi tồn kho để kiểm soát số lượng.
- Quản lý giá nhập và giá bán để tính toán lợi nhuận.

### Quản lý Giao Dịch
- Nhập hàng từ nhà cung cấp.
- Bán hàng cho khách.
- Xem lịch sử giao dịch chi tiết.
- Tìm kiếm giao dịch theo các tiêu chí (ngày, khách hàng, v.v.).

### Thống Kê và Báo Cáo
- Biểu đồ doanh thu theo thời gian.
- Thống kê tồn kho hiện tại.
- Danh sách top vật tư bán chạy.
- Phân tích lợi nhuận từ các giao dịch.

### Phân Quyền Người Dùng
- **Quản lý (Manager)**: Có toàn quyền quản lý hệ thống.
- **Nhân viên (Employee)**: Chỉ thực hiện các thao tác cơ bản, không có quyền quản lý cao cấp.

## 3. Yêu cầu hệ thống
- **Phiên bản**: Python 3.8+ và MySQL 5.7+.
- **Thư viện**: Các thư viện Python cần thiết được liệt kê trong `requirements.txt`, bao gồm:
  - `Flask==3.0.0` (framework web).
  - `mysql-connector-python==8.2.0` (kết nối MySQL).
  - `python-dotenv==1.0.0` (quản lý biến môi trường).
  - `matplotlib==3.8.2` (tạo biểu đồ, có thể dùng để tạo thống kê).

## 4. Hướng dẫn cài đặt
### Clone dự án
- Sử dụng lệnh `git clone <repository-url>` để tải mã nguồn.
- Di chuyển vào thư mục dự án: `cd construction_materials`.

### Tạo môi trường ảo
- Trên Windows: `python -m venv .venv` và kích hoạt bằng `.venv\Scripts\activate`.
- Trên Linux/Mac: `python3 -m venv .venv` và kích hoạt bằng `source .venv/bin/activate`.

### Cài đặt thư viện
- Nâng cấp `pip`: `python -m pip install --upgrade pip`.
- Cài đặt từ `requirements.txt`: `pip install -r requirements.txt`.
- Hoặc cài thủ công từng gói:
  ```
  pip install Flask==3.0.0
  pip install mysql-connector-python==8.2.0
  pip install python-dotenv==1.0.0
  pip install matplotlib==3.8.2
  ```

### Cấu hình cơ sở dữ liệu
- Tạo file `.env` trong thư mục gốc.
- Thêm thông tin kết nối MySQL:
  ```
  MYSQL_HOST=localhost
  MYSQL_USER=your_username
  MYSQL_PASSWORD=your_password
  MYSQL_DATABASE=construction_materials
  MYSQL_PORT=3306
  ```

### Khởi chạy ứng dụng
- Trên Windows: `set FLASK_APP=app.py`, `set FLASK_ENV=development`, sau đó `flask run`.
- Trên Linux/Mac: `export FLASK_APP=app.py`, `export FLASK_ENV=development`, sau đó `flask run`.
- Hoặc chạy trực tiếp: `python app.py`.

### Kiểm tra
- Truy cập `http://localhost:5000`.
- Đăng nhập với tài khoản mặc định:  
  - Username: `admin`  
  - Password: `admin123`

## 5. Xử lý lỗi thường gặp
### Port 5000 bị chiếm dụng
- Windows: `netstat -ano | findstr :5000` để kiểm tra.
- Linux/Mac: `lsof -i :5000` để kiểm tra.
- Giải pháp: Dừng ứng dụng đang sử dụng port đó.

### Lỗi thư viện
- Gỡ cài đặt và cài lại: `pip uninstall -r requirements.txt` rồi `pip install -r requirements.txt`.

### Xóa cache Python
- Windows: `py -3 -m pip cache purge`.
- Linux/Mac: `python3 -m pip cache purge`.

## 6. Cấu trúc thư mục
- **`app.py`**: File chính chứa mã Flask để chạy ứng dụng.
- **`requirements.txt`**: Danh sách thư viện.
- **`.env`**: File cấu hình môi trường (không commit).
- **`.gitignore`**: File cấu hình Git ignore.
- **`README.md`**: Tài liệu hướng dẫn.
- **`static/`**:
  - **`style.css`**: CSS chính cho giao diện.
  - **`responsive-tables.css`**: CSS cho bảng responsive.
  - **`charts/`**: Chứa các file hình ảnh biểu đồ (doanh thu, tồn kho, v.v.).
  - **`icons/`**: Các biểu tượng cho sidebar (quản lý vật tư, giao dịch, thống kê, v.v.).
- **`templates/`**: Chứa các file HTML:
  - **`base.html`**: Template cơ sở.
  - **`login.html`**: Trang đăng nhập.
  - **`materials.html`, `add_material.html`, `edit_material.html`**: Quản lý vật tư.
  - **`purchase.html`, `sell.html`, `orders.html`, `order_detail.html`**: Quản lý giao dịch.
  - **`statistics.html`**: Trang thống kê.
  - **`permissions.html`, `edit_user.html`, `change_password.html`**: Quản lý người dùng.
  - **`no_permission.html`**: Thông báo thiếu quyền.

## 7. Tài khoản mặc định
**Quản lý**:
- Username: `admin`
- Password: `admin123`

## 8. Hướng dẫn sử dụng
### Đăng nhập
- Sử dụng tài khoản được cấp, hệ thống tự điều hướng theo quyền.

### Quản lý Vật Tư
- Thêm: Click "Thêm vật tư mới".
- Tìm kiếm, sửa/xóa: Sử dụng các nút tương ứng trong bảng.

### Giao Dịch
- Nhập hàng: Menu "Nhập hàng".
- Bán hàng: Menu "Bán hàng".
- Xem lịch sử: Menu "Danh sách đơn hàng".

### Thống Kê
- Xem biểu đồ trong menu "Thống kê" (doanh thu, tồn kho, v.v.).

### Bảo mật
- Sử dụng biến môi trường cho thông tin nhạy cảm.
- Phân quyền người dùng chi tiết.
- Kế hoạch mã hóa mật khẩu trong tương lai.
