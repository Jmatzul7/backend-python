from flask_jwt_extended import JWTManager
from flask_cors import CORS
import mysql.connector
from flask import  request, jsonify, Flask
from flask_jwt_extended import jwt_required, create_access_token, get_jwt_identity
from passlib.hash import pbkdf2_sha256
from datetime import datetime, timedelta
import os
import mysql.connector
from dotenv import load_dotenv

app = Flask(__name__)
CORS(app, supports_credentials=True)

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

# Obtener las variables de entorno para la conexión a MySQL
db_host = os.getenv("DB_HOST")
db_user = os.getenv("DB_USERNAME")
db_port = os.getenv("DB_PORT")
db_password = os.getenv("DB_PASSWORD")
db_name = os.getenv("DB_NAMEDABABASE")

# Función para establecer la conexión a MySQL
def get_db_connection():
    try:
        conexion = mysql.connector.connect(
            host=db_host,
            user=db_user,
            port= 3306,
            password=db_password,
            database=db_name
        )
        return conexion
    except mysql.connector.Error as err:
        print(f"Error de conexión a la base de datos: {err}")
        return None


app.config['JWT_SECRET_KEY'] = 'clave_prueba'
app.config['JWT_TOKEN_LOCATION'] = ['cookies']
app.config['JWT_COOKIE_CSRF_PROTECT'] = False
#app.config['SESSION_COOKIE_SECURE'] = True
#app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['WTF_CSRF_ENABLED'] = False
app.config['WTF_CSRF_SECRET_KEY'] = 'clave_secreta_csrf'

jwt = JWTManager(app)
################################################################################
#USER ROUTES
################################################################################
@app.route('/login', methods=['POST'])
def login():
    # Obtener el nombre de usuario y la contraseña del cuerpo de la solicitud JSON
    username = request.json.get('username')
    password = request.json.get('password')

    if not username or not password:
        return jsonify({'error': 'Falta el nombre de usuario o la contraseña'}), 400

    try:
        conexion = get_db_connection()
        if not conexion:
            return jsonify({'error': 'No se pudo conectar a la base de datos'}), 500

        employees = conexion.cursor()

        employees.execute("SELECT password, employee_id, role FROM Employee WHERE username = %s", (username,))
        user_data = employees.fetchone()

        if not user_data or not pbkdf2_sha256.verify(password, user_data[0]):
            return jsonify({'error': 'Credenciales inválidas'}), 401

        user_id = user_data[1]
        role = user_data[2]

        # Generar un token de acceso JWT
        expires_in_days = 1
        expire = datetime.utcnow() + timedelta(days=expires_in_days)
        token_payload = {'username': username, 'user_id': user_id, 'role': role}
        access_token = create_access_token(identity=token_payload, expires_delta=timedelta(days=expires_in_days))

        # Configurar opciones de la cookie
        cookie_options = {
            'httponly': False,
            'expires': expire,
            'secure': False, 
            'samesite': None, 
        }

        # Devolver la respuesta con el token de acceso y la cookie
        response_data = {'access_token': access_token}
        response = jsonify(response_data)
        response.set_cookie('access_token_cookie', value=access_token, **cookie_options)
        return response

    except mysql.connector.Error as e:
        return jsonify({'error': 'Error en la base de datos', 'details': str(e)}), 500

    finally:
        if conexion:
            conexion.close()

@app.route('/protected', methods=['GET'])
@jwt_required()
def protected_route():
    current_user = get_jwt_identity()
    return jsonify({'message': 'Ruta protegida', 'user': current_user}), 200

@app.route('/newUser', methods=['POST'])
@jwt_required()
def create_user():
    if not request.is_json:
        return jsonify({'error': 'El cuerpo de la solicitud debe ser JSON'}), 400

    # Obtén los datos del nuevo usuario del cuerpo de la solicitud JSON
    username = request.json.get('username')
    password = request.json.get('password')
    full_name = request.json.get('full_name')
    role = request.json.get('role')

    # Verifica si los datos del nuevo usuario están completos
    if not username or not password or not full_name or not role:
        return jsonify({'error': 'No puede ir un campo vacío'}), 400

    try:
        conexion = get_db_connection()
        if not conexion:
            return jsonify({'error': 'No se pudo conectar a la base de datos'}), 500

        cursor = conexion.cursor()

        # Verifica si el nombre de usuario ya existe en la base de datos
        cursor.execute("SELECT COUNT(*) FROM Employee WHERE username = %s", (username,))
        existing_user_count = cursor.fetchone()[0]
        if existing_user_count > 0:
            return jsonify({'error': 'El nombre de usuario ya existe'}), 409

        # Inserta el nuevo usuario en la base de datos
        hashed_password = pbkdf2_sha256.hash(password)
        cursor.execute("INSERT INTO Employee (username, password, full_name, role) VALUES (%s, %s, %s, %s)", (username, hashed_password, full_name, role))
        conexion.commit()

        return jsonify({'mensaje': 'Nuevo usuario creado exitosamente'}), 201

    except mysql.connector.Error as e:
        return jsonify({'error': 'Error en la base de datos', 'details': str(e)}), 500

    finally:
        if conexion:
            conexion.close()

@app.route('/getAllUsers', methods=['GET'])
@jwt_required()
def get_all_user():
    try:
        conexion = get_db_connection()
        if not conexion:
            return jsonify({'error': 'No se pudo conectar a la base de datos'}), 500
        
        employees = conexion.cursor()

        # Obtén todos los usuarios de la base de datos
        employees.execute("SELECT * FROM Employee")
        users = employees.fetchall()

        # Formatea los datos de los usuarios en una lista de diccionarios
        users_data = []
        for user in users:
            user_data = {
                'username': user[1],
                'full_name': user[3],
                'role': user[4]
            }
            users_data.append(user_data)

        return jsonify({'users': users_data}), 200
    except mysql.connector.Error as e:
        return jsonify({'error': 'Error en la base de datos', 'details': str(e)}), 500
    
    finally:
        if conexion:
            conexion.close()

@app.route('/getUser/<username>', methods=['GET'])
@jwt_required()
def get_user(username):
    conexion = None
    try:
        # Obtiene el usuario logueado desde el token JWT
        current_user = get_jwt_identity()
        name = current_user['username']

        # Verifica si el usuario logueado coincide con el usuario solicitado
        if name != username:
            return jsonify({'error': 'No tienes permiso para acceder a estos datos'}), 403
        
        conexion = get_db_connection()
        employees = conexion.cursor()

        # Obtén los datos del usuario de la base de datos
        employees.execute("SELECT * FROM Employee WHERE username = %s", (username,))
        user = employees.fetchone()

        if user is None:
            return jsonify({'error': 'El usuario no existe'}), 404
        
        user_data = {
            'username': user[1],
            'full_name': user[3],
            'role': user[4]
        }

        return jsonify({'usuario': user_data}), 200

    except mysql.connector.Error as e:
        return jsonify({'error': 'Error en la base de datos', 'details': str(e)}), 500
    
    finally:
        if conexion:
            conexion.close()

@app.route('/deleteUser/<username>', methods=['DELETE'])
@jwt_required()
def delete_user(username):
    try:
        conexion =get_db_connection()
        if not conexion:
            return jsonify({'error': 'No se pudo conectar a la base de datos'}), 500
        
        employees = conexion.cursor()

        # Verifica si el usuario existe en la base de datos
        employees.execute("SELECT COUNT(*) FROM Employee WHERE username = %s", (username,))
        existing_user_count = employees.fetchone()[0]

        if existing_user_count == 0:
            return jsonify({'error': 'El usuario no existe'}), 404
        
        # Elimina el usuario de la base de datos
        employees.execute("DELETE FROM Employee WHERE username = %s", (username,))
        conexion.commit()

        return jsonify({'mensaje': 'Usuario eliminado exitosamente'}), 200
    
    except mysql.connector.Error as e:
        return jsonify({'error': 'Error en la base de datos', 'details': str(e)}), 500
    
    finally: 
        if conexion:
            conexion.close()

@app.route('/updateUser/<username>', methods=['PUT'])
@jwt_required()
def update_user(username):
    current_password = request.json.get('current_password')
    new_username = request.json.get('new_username')
    new_password = request.json.get('new_password')
    new_full_name = request.json.get('new_full_name')
    new_role = request.json.get('new_role')

    if not current_password:
        return jsonify({'error': 'Debes ingresar tu contraseña actual'}), 400
    
    try:
        conexion = get_db_connection()
        employees = conexion.cursor()

        employees.execute("SELECT password FROM Employee WHERE username = %s", (username,))
        user_data = employees.fetchone()

        if not user_data:
            return jsonify({'error': 'El usuario no existe'}), 404

        hashed_password = user_data[0]
        if not pbkdf2_sha256.verify(current_password, hashed_password):
            return jsonify({'error': 'Contraseña actual incorrecta'}), 401 

        update_query = "UPDATE Employee SET"
        update_params = []

        if new_username:
            # Verificar si el nuevo nombre de usuario ya existe
            employees.execute("SELECT * FROM Employee WHERE username = %s", (new_username,))
            existing_user = employees.fetchone()

        if existing_user:
                return jsonify({'error': 'Nombre de usuario existente. Intenta con otro nombre de usuario'}), 400
        
        update_query += " username = %s,"
        update_params.append(new_username)

        if new_password:
            hashed_new_password = pbkdf2_sha256.hash(new_password)
            update_query += " password = %s,"
            update_params.append(hashed_new_password)

        if new_full_name:
            update_query += " full_name = %s,"
            update_params.append(new_full_name)

        if new_role:
            update_query += " role = %s,"
            update_params.append(new_role)

        update_query = update_query.rstrip(',')
        update_params.append(username)

        employees.execute(update_query + " WHERE username = %s", update_params)
        conexion.commit()

        return jsonify({'message': 'Usuario actualizado exitosamente'}), 200
    
    except mysql.connector.Error as e:
        return jsonify({'error': 'Error en la base de datos', 'details': str(e)}), 500
    
    finally: 
        if conexion:
            conexion.close()

################################################################################
#CUSTOMERS ROUTES
################################################################################


@app.route('/newCustomer', methods=['POST'])
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

@app.route('/getCustomer/<customer_id>', methods=['GET'])
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

@app.route('/getCustomers', methods=['GET'])
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


@app.route('/getTopCustomers', methods=['GET'])
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


@app.route('/getCustomerSale', methods=['GET'])
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

@app.route('/getCustomerServices/<customer_id>', methods=['GET'])
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

@app.route('/updateCustomer/<customer_id>', methods=['PUT'])
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



################################################################################
#SERVICES ROUTES
################################################################################


@app.route('/newServices', methods=['POST'])
@jwt_required()
def create_service():
    if not request.is_json:
        return jsonify({'error': 'El cuerpo de la solicitud debe ser JSON'}), 400
    
    # # Obtén los datos del nuevo servicio del cuerpo de la solicitud JSON
    service_name = request.json.get('service_name')
    service_type = request.json.get('service_type')
    price = request.json.get('price')
    availability = request.json.get('availability')

    # Verifica si los datos del nuevo servicio están completos
    if not service_name or not service_type or not price or not availability:
        return jsonify({'error': 'Faltan campos obligatorios para crear el servicio'}), 400

    try:
        conexion = get_db_connection()
        services = conexion.cursor()

        # Inserta el nuevo servicio en la base de datos
        services.execute("INSERT INTO Services (service_name, service_type, price, availability) VALUES (%s, %s, %s, %s)",
                        (service_name, service_type, price, availability))
        conexion.commit()

        return jsonify({'mensaje': 'Nuevo servicio creado exitosamente'}), 201

    except mysql.connector.Error as e:
        return jsonify({'error': 'Error en la base de datos', 'details': str(e)}), 500

    finally:
        if conexion:
            conexion.close

@app.route('/getAllServices', methods=['GET'])
@jwt_required()
def get_all_services():
    try:
        conexion = get_db_connection()
        services = conexion.cursor()

        # Obtén todos los servicios de la base de datos
        services.execute("SELECT * FROM Services")
        services_data = services.fetchall()

        # Formatea los datos de los servicios en una lista de diccionarios
        services_list = []
        for service in services_data:
            service_dict = {
                'service_id': service[0],
                'service_name': service[1],
                'service_type': service[2],
                'price': service[3],
                'availability': service[4],
                'sales_count': service[5]
            }
            services_list.append(service_dict)

        return jsonify({'services': services_list}), 200
    
    except mysql.connector.Error as e:
        return jsonify({'error': 'Error en la base de datos', 'details': str(e)}), 500
    
    finally:
        if conexion:
            conexion.close()

@app.route('/getServices/<service_id>', methods=['GET'])
@jwt_required()
def get_service(service_id):
    try:
        conexion = get_db_connection()
        services = conexion.cursor()

        # Obtén los datos del servicio de la base de datos
        services.execute("SELECT * FROM Services WHERE service_id = %s", (service_id,))
        service = services.fetchone()

        if service is None:
            return jsonify({'Error': 'El servicio no existe'}), 404
        
        # Formatea los datos del servicio en un diccionario
        service_dict = {
            'service_id': service[0],
            'service_name': service[1],
            'service_type': service[2],
            'price': service[3],
            'availability': service[4]
        }
        return jsonify(service_dict), 200
    
    except mysql.connector.Error as e:
        return jsonify({'Error': 'Error en la base de datos', 'Details': str(e)}), 500
    
    finally:
        if conexion:
            conexion.close

@app.route('/updateServices/<service_id>', methods=['PUT'])
@jwt_required()
def update_service(service_id):
    if not request.is_json:
        return jsonify({'error': 'El cuerpo de la solicitud debe ser JSON'}), 400
    
    # Obtén los datos actualizados del servicio del cuerpo de la solicitud JSON
    service_name = request.json.get('service_name')
    service_type = request.json.get('service_type')
    price = request.json.get('price')
    availability = request.json.get('availability')

    try:
        conexion = get_db_connection()
        services = conexion.cursor()

        # Verifica si el servicio existe en la base de datos
        services.execute("SELECT COUNT(*) FROM Services WHERE service_id = %s", (service_id,))
        existing_service_count = services.fetchone()[0]
        if existing_service_count == 0:
            return jsonify({'error': 'El servicio no existe'}), 404
        
        # Actualiza los datos del servicio en la base de datos
        services.execute("UPDATE Services SET service_name = %s, service_type = %s, price = %s, availability = %s "
                         "WHERE service_id = %s",
                         (service_name, service_type, price, availability, service_id))
        conexion.commit()

        return jsonify({'mensaje': 'Servicio actualizado exitosamente'}), 200

    except mysql.connector.Error as e:
        return jsonify({'error': 'Error en la base de datos', 'details': str(e)}), 500

    finally:
        if conexion:
            conexion.close()

@app.route('/deleteServices/<service_id>', methods=['DELETE'])
@jwt_required()
def delete_service(service_id):
    try:
        conexion = get_db_connection()
        services = conexion.cursor()

        # Verifica si el servicio existe en la base de datos
        services.execute("SELECT COUNT(*) FROM Services WHERE service_id = %s", (service_id,))
        existing_service_count = services.fetchone()[0]
        if existing_service_count == 0:
            return jsonify({'error': 'El servicio no existe'}), 404
        
        # Elimina el servicio de la base de datos
        services.execute("DELETE FROM Services WHERE service_id = %s", (service_id,))
        conexion.commit()

        return jsonify({'mensaje': 'Servicio eliminado exitosamente'}), 200
    
    except mysql.connector.Error as e:
        return jsonify({'error': 'Error en la base de datos', 'details': str(e)}), 500
    
    finally:
        if conexion:
            conexion.close()



################################################################################
#SALES ROUTES
################################################################################



@app.route('/newSale', methods=['POST'])
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

@app.route('/sales', methods=['GET'])
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

@app.route('/sales/<int:sale_id>', methods=['GET'])
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

@app.route('/delete/<int:sale_id>', methods=['DELETE'])
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

@app.route('/getLatestSales', methods=['GET'])
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





if __name__ == '__main__':
    app.run(debug=True)