from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
import mysql.connector
from DB_MYSQL.connection import get_db_connection

customer_bp = Blueprint('customer_bp', __name__)

@customer_bp.route('/newCustomer', methods=['POST'])
@jwt_required()
def create_customer():
    if not request.is_json:
        return jsonify({'error': 'El cuerpo de la solicitud debe ser JSON'}), 400

    # Obtén los datos del nuevo cliente del cuerpo de la solicitud JSON
    data = request.json
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    age = data.get('age')
    gender = data.get('gender')
    contact_number = data.get('contact_number')
    email = data.get('email')
    address = data.get('address')

    # Verifica si los datos del nuevo cliente están completos
    if not first_name or not last_name or not age or not gender or not contact_number or not email or not address:
        return jsonify({'error': 'No puede haber campos vacíos'}), 400

    try:
        # Conecta a la base de datos MySQL
        conexion = get_db_connection()
        customers = conexion.cursor()

        # Inserta el nuevo cliente en la base de datos
        insert_query = "INSERT INTO Customers (first_name, last_name, age, gender, contact_number, email, address) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        customers.execute(insert_query, (first_name, last_name, age, gender, contact_number, email, address))
        conexion.commit()

        return jsonify({'mensaje': 'Nuevo cliente creado exitosamente'}), 201

    except mysql.connector.Error as e:
        return jsonify({'error': 'Error en la base de datos', 'details': str(e)}), 500

    finally:
        customers.close()
        conexion.close()

@customer_bp.route('/getCustomer/<customer_id>', methods=['GET'])
@jwt_required()
def get_customer(customer_id):
    try:
        conexion = get_db_connection()
        customers = conexion.cursor()

        # Obtén los datos del cliente específico de la base de datos
        customers.execute("SELECT * FROM Customers WHERE customer_id = %s", (customer_id,))
        customer_data = customers.fetchone()

        if customer_data is None:
            return jsonify({'Error': 'El cliente no existe'}), 404
        
        # Formatea los datos del cliente en un diccionario
        customer_dict = {
            'customer_id': customer_data[0],
            'first_name': customer_data[1],
            'last_name': customer_data[2],
            'age': customer_data[3],
            'gender': customer_data[4],
            'contact_number': customer_data[5],
            'email': customer_data[6],
            'address': customer_data[7]
        }

        return jsonify({'customer': customer_dict}), 200
    
    except mysql.connector.Error as e:
        return jsonify({'error': 'Error en la base de datos', 'details': str(e)}), 500
    
    finally:
        if conexion:
            conexion.close()

@customer_bp.route('/getCustomers', methods=['GET'])
@jwt_required()
def get_customers():
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor()

        # Obtén todos los clientes de la base de datos
        cursor.execute("SELECT * FROM Customers")
        customer_data = cursor.fetchall()

        # Formatea los datos de los clientes en una lista de diccionarios
        customers_list = []
        for customer in customer_data:
            customer_dict = {
                'customer_id': customer[0],
                'first_name': customer[1],
                'last_name': customer[2],
                'age': customer[3],
                'gender': customer[4],
                'contact_number': customer[5],
                'email': customer[6],
                'address': customer[7],
                'services_purchased': customer[8]
            }
            customers_list.append(customer_dict)

        return jsonify({'customers': customers_list}), 200

    except mysql.connector.Error as e:
        return jsonify({'error': 'Error en la base de datos', 'details': str(e)}), 500

    finally:
        cursor.close()
        if conexion:
            conexion.close()


@customer_bp.route('/getTopCustomers', methods=['GET'])
@jwt_required()
def get_top_customers():
    try:
        conexion = get_db_connection()
        customers = conexion.cursor()
        # Obtén los 5 clientes que han adquirido más servicios
        customers.execute("SELECT * FROM Customers ORDER BY services_purchased DESC LIMIT 5")
        customer_data = customers.fetchall()

        # Formatea los datos de los clientes en una lista de diccionarios
        customers_list = []
        for customer in customer_data:
            customer_dict = {
                'customer_id': customer[0],
                'first_name': customer[1],
                'last_name': customer[2],
                'age': customer[3],
                'gender': customer[4],
                'contact_number': customer[5],
                'email': customer[6],
                'address': customer[7],
                'services_purchased': customer[8]
            }
            customers_list.append(customer_dict)

        return jsonify({'customers': customers_list}), 200
        
    except mysql.connector.Error as e:
         return jsonify({'error': 'Error en la base de datos', 'details': str(e)}), 500
    
    finally:
        if conexion:
            conexion.close()


@customer_bp.route('/getCustomerSale', methods=['GET'])
@jwt_required()
def get_customers_sale():
    try:
        conexion = get_db_connection()
        customers = conexion.cursor()

        # Obtén todos los clientes de la base de datos
        customers.execute("SELECT customer_id, first_name, last_name, age, gender, contact_number, email, address FROM Customers")
        customer_data = customers.fetchall()

        # Formatea los datos de los clientes en una lista de diccionarios
        customers_list = []
        for customer in customer_data:
            customer_dict = {
                'customer_id': customer[0],
                'first_name': customer[1],
                'last_name': customer[2],
                'age': customer[3],
                'gender': customer[4],
                'contact_number': customer[5],
                'email': customer[6],
                'address': customer[7],
            }
            customers_list.append(customer_dict)

        return jsonify({'customers': customers_list}), 200
    
    except mysql.connector.Error as e:
        return jsonify({'error': 'Error en la base de datos', 'details': str(e)}), 500
    
    finally:
        if conexion:
            conexion.close

@customer_bp.route('/getCustomerServices/<customer_id>', methods=['GET'])
@jwt_required()
def get_customer_services(customer_id):
    try:
        conexion = get_db_connection()
        customers = conexion.cursor()

        # Verifica si el cliente existe
        customers.execute("SELECT * FROM Customers WHERE customer_id = %s", (customer_id,))
        customer_data = customers.fetchone()
        if customer_data is None:
            return jsonify({'error': 'El cliente no existe'}), 404
        
        # Obtiene los servicios asociados al cliente desde la tabla CustomerServices
        query = """
        SELECT Services.service_name, Services.service_type, Services.price, Sales.sale_date
        FROM CustomerServices
        JOIN Services ON CustomerServices.service_id = Services.service_id
        JOIN Sales ON CustomerServices.sale_id = Sales.sale_id
        WHERE CustomerServices.customer_id = %s
        """
        customers.execute(query, (customer_id,))
        services_data = customers.fetchall()

        # Formatea los servicios en una lista de diccionarios
        services = []
        for service in services_data:
            service_dict = {
                'service_name': service[0],
                'service_type': service[1],
                'price': service[2],
                'sale_date': service[3]
            }
            services.append(service_dict)

        return jsonify({'services': services}), 200
    
    except mysql.connector.Error as e:
        return jsonify({'error': 'Error en la base de datos', 'details': str(e)}), 500
    
    finally:
        if conexion:
            conexion.close()

@customer_bp.route('/updateCustomer/<customer_id>', methods=['PUT'])
@jwt_required()
def update_customer(customer_id):
    if not request.is_json:
        return jsonify({'error': 'El cuerpo de la solicitud debe ser JSON'}), 400
    
     # Obtén los datos actualizados del cliente del cuerpo de la solicitud JSON
    new_first_name = request.json.get('first_name')
    new_last_name = request.json.get('last_name')
    new_age = request.json.get('age')
    new_gender = request.json.get('gender')
    new_contact_number = request.json.get('contact_number')
    new_email = request.json.get('email')
    new_address = request.json.get('address')

    if not new_first_name and not new_last_name and not new_age and not new_gender and not new_contact_number and not new_email and not new_address:
        return jsonify({'error': 'No se proporcionaron nuevos datos para actualizar'}), 400
    try:
        conexion = get_db_connection()
        customers = conexion.cursor()

            # Verifica si el cliente existe en la base de datos
        customers.execute("SELECT COUNT(*) FROM Customers WHERE customer_id = %s", (customer_id,))
        existing_customer_count = customers.fetchone()[0]
        if existing_customer_count == 0:
            return jsonify({'error': 'El cliente no existe'}), 404
        
        # Actualiza los datos del cliente en la base de datos
        update_query = "UPDATE Customers SET"
        update_params = []

        if new_first_name:
            update_query += " first_name = ?,"
            update_params.append(new_first_name)

        if new_last_name:
            update_query += " last_name = ?,"
            update_params.append(new_last_name)

        if new_age:
            update_query += " age = ?,"
            update_params.append(new_age)

        if new_gender:
            update_query += " gender = ?,"
            update_params.append(new_gender)

        if new_contact_number:
            update_query += " contact_number = ?,"
            update_params.append(new_contact_number)

        if new_email:
            update_query += " email = ?,"
            update_params.append(new_email)

        if new_address:
            update_query += " address = ?,"
            update_params.append(new_address)

            # Elimina la coma final de la consulta de actualización
            update_query = update_query.rstrip(',')

            # Agrega el parámetro para el ID del cliente de la actualización
            update_params.append(customer_id)

            # Ejecuta la consulta de actualización
            customers.execute(update_query + " WHERE customer_id = %s", update_params)
            conexion.commit()

            return jsonify({'mensaje': 'Cliente actualizado exitosamente'}), 200
    
    except mysql.connector.Error as e:
        return jsonify({'mensaje': 'Cliente actualizado exitosamente'}), 200
    
    finally:
        if conexion:
            conexion.close()
