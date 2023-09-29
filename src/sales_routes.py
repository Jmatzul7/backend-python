from datetime import datetime, timedelta
import time
from flask import Blueprint, jsonify, request
from flask_jwt_extended import  get_jwt_identity, jwt_required
import mysql.connector
from DB_MYSQL.connection import get_db_connection

sales_bp = Blueprint('sales_bp', __name__)

@sales_bp.route('/newSale', methods=['POST'])
@jwt_required()
def create_sale_new():
    if not request.is_json:
        return jsonify({'error': 'El cuerpo de la solicitud debe ser JSON'}), 400

    try:
        with get_db_connection() as con:
            sales = con.cursor()

            # Obtén el ID del usuario logueado
            current_user_id = get_jwt_identity()
            user_id = current_user_id['user_id']
            username = current_user_id['username']

            # Obtén los datos de la venta del cuerpo de la solicitud JSON
            customer_data = request.json.get('customer')
            service_id = request.json.get('service_id')
            additional_info = request.json.get('additional_info')
            customer_id = customer_data.get('customer_id')
            

            # Verifica si los datos de la venta están completos
            if not customer_data or not service_id or customer_id is None:
                return jsonify({'error': 'Los datos de la venta están incompletos'}), 400

            if customer_id == 0:
                # Crea el nuevo cliente
                customers = con.cursor()
                customers.execute("""
                    INSERT INTO Customers (first_name, last_name, age, gender, contact_number, email, address, services_purchased)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    customer_data['first_name'],
                    customer_data['last_name'],
                    customer_data['age'],
                    customer_data['gender'],
                    customer_data['contact_number'],
                    customer_data['email'],
                    customer_data['address'],
                    0  # Inicializa la cantidad de servicios adquiridos en 0
                ))
                customer_id = customers.lastrowid
                services_purchased = 0
            else:
                # Verifica si el cliente ya existe
                customers = con.cursor()
                customers.execute("""
                    SELECT customer_id, services_purchased FROM Customers
                    WHERE customer_id = %s
                """, (customer_id,))
                existing_customer = customers.fetchone()

                if existing_customer:
                    customer_id = existing_customer[0]
                    services_purchased = existing_customer[1]
                else:
                    return jsonify({'error': 'El cliente no existe'}), 404

            # Obtiene el nombre del cliente
            customer_name = f"{customer_data['first_name']} {customer_data['last_name']}"

            # Verifica la disponibilidad del servicio
            services = con.cursor()
            services.execute("SELECT service_name, service_type, sales_count, availability FROM Services WHERE service_id = %s", (service_id,))
            service_data = services.fetchone()

            if not service_data:
                return jsonify({'error': 'El servicio no existe'}), 404
            
            if not service_data[3]:
                return jsonify({'error': 'El servicio no está disponible'}), 400
            # Accede a las columnas por índices numéricos
            service_name = service_data[0]
            service_type = service_data[1]
            current_sales_count = service_data[2]
            availability = service_data[3]

           # Obtén la fecha y hora actual en la zona horaria local del servidor
            sale_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(sale_date)
            # Crea la venta asociada al cliente, servicio y usuario logueado
            sales.execute("""
                INSERT INTO Sales (employee_id, customer_id, service_id, sale_date, additional_info)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, customer_id, service_id, sale_date, additional_info))

            sale_id = sales.lastrowid

            # Actualiza la cantidad de ventas del servicio
            updated_sales_count = current_sales_count + 1
            services.execute("UPDATE Services SET sales_count = %s WHERE service_id = %s", (updated_sales_count, service_id))

            # Inserta el servicio en la tabla CustomerServices
            customer_services = con.cursor()
            customer_services.execute("""
                INSERT INTO CustomerServices (customer_id, service_id, sale_id)
                VALUES (%s, %s, %s)
            """, (customer_id, service_id, sale_id))

            # Actualiza la cantidad de servicios adquiridos por el cliente
            services_purchased += 1
            customers.execute("UPDATE Customers SET services_purchased = %s WHERE customer_id = %s", (services_purchased, customer_id))

            # Confirma los cambios en la base de datos
            con.commit()

            return jsonify({
                'message': 'Venta creada exitosamente',
                'cliente': customer_name,
                'usuario': username,
                'servicio': service_name,
                'servicio_type': service_type,
                'fecha': sale_date
            }), 201

    except mysql.connector.Error as e:
        return jsonify({'error': 'Error en la base de datos', 'details': str(e)}), 500

    finally:
        if con:
            con.close

@sales_bp.route('/sales', methods=['GET'])
@jwt_required()
def get_all_sales():
    try:
        with get_db_connection() as conexion:
            sales = conexion.cursor()

            # Obtén el ID del usuario logueado
            current_user_id = get_jwt_identity()
            user_id = current_user_id['user_id']

            # Obtén todas las ventas del usuario logueado
            sales.execute("""
                SELECT Sales.sale_id, Sales.sale_date, Employee.username, Customers.first_name, Customers.last_name, Services.service_name, Services.service_type
                FROM Sales
                INNER JOIN Employee ON Sales.employee_id = Employee.employee_id
                INNER JOIN Customers ON Sales.customer_id = Customers.customer_id
                INNER JOIN Services ON Sales.service_id = Services.service_id
                WHERE Sales.employee_id = %s
            """, (user_id,))
            sales_data = sales.fetchall()

            # Lista para almacenar los detalles de las ventas
            sales_list = []
            
            for sale in sales_data:
                sale_id = sale[0]
                sale_date = sale[1]
                username = sale[2]
                customer_name = f"{sale[3]} {sale[4]}"
                service_name = sale[5]
                service_type = sale[6]
                

                sales_list.append({
                    'sale_id': sale_id,
                    'user': username,
                    'customer': customer_name,
                    'service': service_name,
                    'service_type': service_type,
                    'sale_date': sale_date
                })

            return jsonify({'sales': sales_list}), 200
        
    except mysql.connector.Error as e:
        return jsonify({'error': 'Error en la base de datos', 'details': str(e)}), 500
    
    finally:
        if conexion:
            conexion.close()

@sales_bp.route('/sales/<int:sale_id>', methods=['GET'])
@jwt_required()
def get_sale_details(sale_id):
    try:
        with get_db_connection() as conexion:
            sales = conexion.cursor()

            # Obtén el ID del usuario logueado
            current_user_id = get_jwt_identity()
            user_id = current_user_id['user_id']

            # Verifica si la venta existe y pertenece al usuario logueado
            sales.execute("SELECT * FROM Sales WHERE sale_id = %s AND employee_id = %s", (sale_id, user_id))
            sale = sales.fetchone()
            if sale is None:
                return jsonify({'error': 'La venta no existe o no tienes permisos para acceder a ella'}), 404
            
            # Obtiene el nombre del usuario
            users = conexion.cursor()
            users.execute("SELECT username FROM Employee WHERE employee_id = %s", (user_id,))
            username = users.fetchone()[0]
            
            # Obtiene el nombre del cliente
            customer_id = sale[2]  # Asumiendo que el customer_id está en la segunda columna
            customers = conexion.cursor()
            customers.execute("SELECT first_name, last_name FROM Customers WHERE customer_id = %s", (customer_id,))
            customer = customers.fetchone()
            if customer is None:
                return jsonify({'error': 'El cliente asociado a la venta no existe'}), 404
            customer_name = f"{customer[0]} {customer[1]}"

            # Obtiene el nombre del servicio y el tipo de servicio
            service_id = sale[1]  # Asumiendo que el service_id está en la tercera columna
         
            services = conexion.cursor()
            services.execute("SELECT service_name, service_type FROM Services WHERE service_id = %s", (service_id,))
            service = services.fetchone()

            if service is None:
                return jsonify({'error': 'Ningun servicio asociado o a la venta'}), 404
            
            service_name = service[0]
            service_type = service[1]
            
            return jsonify({
                'sale_id': sale_id,
                'user': username,
                'customer': customer_name,
                'service': service_name,
                'service_type': service_type
            }), 200
        
    except mysql.connector.Error as e:
        return jsonify({'error': 'Error en la base de datos', 'details': str(e)}), 500

    finally:
        if conexion:
            conexion.close()

@sales_bp.route('/delete/<int:sale_id>', methods=['DELETE'])
@jwt_required()
def delete_sale(sale_id):
    conexion = None
    try:
        conexion = get_db_connection()
        sales = conexion.cursor()

        # Verifica si la venta existe
        sales.execute("SELECT * FROM Sales WHERE sale_id = %s", [sale_id],)
        sale = sales.fetchone()

        if sale is None:
            return jsonify({'Error': 'La venta no existe'}), 404
        
        # Obtiene los datos de la venta
        customer_id = sale[2]
        service_id = sale[3]

        # Elimina los registros en la tabla CustomerServices primero
        customer_services = conexion.cursor()
        customer_services.execute("DELETE FROM CustomerServices WHERE sale_id = %s", (sale_id,))
        conexion.commit()

        # Elimina la venta después de eliminar los registros en CustomerServices
        sales.execute("DELETE FROM Sales WHERE sale_id = %s", (sale_id,))
        conexion.commit()

        # Verifica si el cliente tiene más ventas asociadas
        sales.execute("SELECT COUNT(*) FROM Sales WHERE customer_id = %s", (customer_id,))
        count = sales.fetchone()[0]

        if count == 0:
            # Si es la última venta del cliente, elimina al cliente
            customers = conexion.cursor()
            customers.execute("DELETE FROM Customers WHERE customer_id = %s", (customer_id,))
            conexion.commit()
        else:
            # Si no es la última venta del cliente, actualiza la cantidad de servicios adquiridos
            customers = conexion.cursor()
            customers.execute("UPDATE Customers SET services_purchased = services_purchased - 1 WHERE customer_id = %s", (customer_id,))
            conexion.commit()

        # Actualiza la cantidad de ventas del servicio
        services = conexion.cursor()
        services.execute("UPDATE Services SET sales_count = sales_count - 1 WHERE service_id = %s", (service_id,))
        conexion.commit()

        return jsonify({'mensaje': 'Venta eliminada exitosamente'}), 200
        
    except mysql.connector.Error as e:
        return jsonify({'error': 'Error en la base de datos', 'details': str(e)}), 500
    
    finally:
        if conexion:
            conexion.close()

@sales_bp.route('/getLatestSales', methods=['GET'])
@jwt_required()
def get_latest_sales():
    try:
        with get_db_connection() as conexion:
            sales = conexion.cursor()

            # Obtén las últimas 5 ventas ordenadas por fecha de venta
            sales.execute("""
                SELECT Sales.sale_id, Employee.username, Customers.first_name, Customers.last_name, Services.service_name, Services.service_type
                FROM Sales
                INNER JOIN employee ON Sales.employee_id = Employee.employee_id
                INNER JOIN Customers ON Sales.customer_id = Customers.customer_id
                INNER JOIN Services ON Sales.service_id = Services.service_id
                ORDER BY Sales.sale_date DESC
                LIMIT 5
            """)
            sales_data = sales.fetchall()
            
        
            # Lista para almacenar los detalles de las ventas
            sales_list = []

            for sale in sales_data:
                sale_id = sale[0]
                username = sale[1]
                customer_name = f"{sale[2]} {sale[3]}"
                service_name = sale[4]
                service_type = sale[5]

                sales_list.append({
                    'sale_id': sale_id,
                    'user': username,
                    'customer': customer_name,
                    'service': service_name,
                    'service_type': service_type
                })

            return jsonify({'sales': sales_list}), 200
            
    except mysql.connector.Error as e:
        return jsonify({'error': 'Error en la base de datos', 'details': str(e)}), 500
    
    finally: 
        if conexion:
            conexion.close()


