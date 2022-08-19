import os
from datauploader import create_app
application = create_app(os.environ.get('FLASK_CONFIG') or 'default')
