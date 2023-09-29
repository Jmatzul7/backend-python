from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
import mysql.connector
from DB_MYSQL.connection import get_db_connection

services_bp = Blueprint('services_bp', __name__)

@services_bp.route('/newServices', methods=['POST'])
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

@services_bp.route('/getAllServices', methods=['GET'])
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

@services_bp.route('/getServices/<service_id>', methods=['GET'])
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

@services_bp.route('/updateServices/<service_id>', methods=['PUT'])
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

@services_bp.route('/deleteServices/<service_id>', methods=['DELETE'])
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



