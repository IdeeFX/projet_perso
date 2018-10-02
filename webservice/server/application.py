
#!/usr/bin/env python
import logging
import os
import socket
from setproctitle import setproctitle
from werkzeug.wsgi import DispatcherMiddleware
from webservice.server.soapInterface import wsgi_application
from flask import Flask, render_template, request
from utils.log_setup import setup_logging
from utils.database import Database
from utils.setup_tree import HarnessTree
from settings.settings_manager import SettingsManager
from utils.const import PORT, ENV


# TODO allow to pass into arguments a custom settings file
SettingsManager.load_settings()

# initialize LOGGER
setup_logging()
LOGGER = logging.getLogger(__name__)
LOGGER.debug("Logging configuration set up in %s", __name__)

# setup repertory structure
HarnessTree.setup_tree()

DIRNAME = os.path.dirname(__file__)
APP = Flask(__name__)
# SOAP services are distinct wsgi applications so we are using middleware to bring all aps together
APP.wsgi_app = DispatcherMiddleware(APP.wsgi_app, {
    '/harnais-diss-v2/webservice/Dissemination': wsgi_application
})

# Setting up database
Database.initialize_database(APP)
LOGGER.info("setup complete")

def main():
    setproctitle("harness_soap_server")

    hostname = socket.gethostname()
    port = os.environ.get(ENV.port) or PORT
    LOGGER.warning("Starting application through Flask development server."
                   " This is NOT a production environment.")
    LOGGER.info("Launching Flask development server "
                "on hostname %s on port %i", hostname, port)
    APP.run(host=hostname, port=port)
    # WARNING You might run into the spyne error :
    # ValueError: '__class__' is not in list
    # in odict.py if you run this code using an IDE debugger.
    # A possible fix is there https://github.com/arskom/spyne/pull/572

if __name__ == '__main__':
    main()

