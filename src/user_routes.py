import mysql.connector
from flask import  request, jsonify, Blueprint
from flask_jwt_extended import jwt_required, create_access_token, get_jwt_identity
from passlib.hash import pbkdf2_sha256
from datetime import datetime, timedelta
from DB_MYSQL.connection import get_db_connection

users_bp = Blueprint('users_bp', __name__)

@users_bp.route('/login', methods=['POST'])
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
            'httponly': True,
            'expires': expire,
            'secure': True,  
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

@users_bp.route('/protected', methods=['GET'])
@jwt_required()
def protected_route():
    current_user = get_jwt_identity()
    return jsonify({'message': 'Ruta protegida', 'user': current_user}), 200

@users_bp.route('/newUser', methods=['POST'])
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

@users_bp.route('/getAllUsers', methods=['GET'])
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

@users_bp.route('/getUser/<username>', methods=['GET'])
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

@users_bp.route('/deleteUser/<username>', methods=['DELETE'])
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

@users_bp.route('/updateUser/<username>', methods=['PUT'])
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
