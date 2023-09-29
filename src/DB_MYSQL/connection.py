import os
import mysql.connector
from dotenv import load_dotenv

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

