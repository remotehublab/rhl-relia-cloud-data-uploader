import sys
from flask import Flask
from flask_redis import FlaskRedis

from config import configurations

# Plugins
redis_store = FlaskRedis()


def create_app(config_name: str = 'default'):

    # Based on Flasky https://github.com/miguelgrinberg/flasky
    app = Flask(__name__)
    app.config.from_object(configurations[config_name])

    if config_name in ['development', 'default'] and '--with-threads' not in sys.argv and 'run' in sys.argv:
        print("***********************************************************")
        print("*                                                         *")
        print("*               I M P O R T A N T                         *")
        print("*                                                         *")
        print("* You must pass --with-threads when testing data-uploader *")
        print("*                                                         *")
        print("***********************************************************")


    # Initialize plugins
    redis_store.init_app(app)


    # Register views
    from .views import main_blueprint, api_blueprint

    app.register_blueprint(main_blueprint)
    app.register_blueprint(api_blueprint, url_prefix='/api')

    return app
