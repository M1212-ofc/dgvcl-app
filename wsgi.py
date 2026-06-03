# ---------------------------------------------------------------
# PythonAnywhere WSGI file
# In PythonAnywhere → Web tab → WSGI configuration file,
# replace the contents with this file.
# ---------------------------------------------------------------
import sys, os

# Path to your project folder on PythonAnywhere
# Replace 'yourusername' with your actual PythonAnywhere username
project_home = '/home/yourusername/dgvcl_app'

if project_home not in sys.path:
    sys.path.insert(0, project_home)

os.chdir(project_home)

from app import app as application
from database import init_db

init_db()
