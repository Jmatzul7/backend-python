from flask import Flask
from flask_jwt_extended import JWTManager
from flask_cors import CORS

app = Flask(__name__)
CORS(app, supports_credentials=True)

from customer_routes import customer_bp
from services_routes import services_bp
from sales_routes import sales_bp
from user_routes import users_bp


app.config['JWT_SECRET_KEY'] = 'clave_prueba'
app.config['JWT_TOKEN_LOCATION'] = ['cookies']
app.config['JWT_COOKIE_CSRF_PROTECT'] = False
#app.config['SESSION_COOKIE_SECURE'] = True
#app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['WTF_CSRF_ENABLED'] = False
app.config['WTF_CSRF_SECRET_KEY'] = 'clave_secreta_csrf'

jwt = JWTManager(app)

app.register_blueprint(users_bp)

app.register_blueprint(customer_bp)

app.register_blueprint(services_bp)

app.register_blueprint(sales_bp)

if __name__ == '__main__':
    app.run(debug=True)