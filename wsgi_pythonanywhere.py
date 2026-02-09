"""
WSGI Configuration for PythonAnywhere

Instructions:
1. Upload all DATARADAR files to /home/YOUR_USERNAME/DATARADAR/
2. In PythonAnywhere Web tab, set Source code to: /home/YOUR_USERNAME/DATARADAR
3. Set WSGI configuration file to this file's path
4. Or copy this content to the auto-generated WSGI file

Replace YOUR_USERNAME with your actual PythonAnywhere username below.
"""

import sys
import os

# Add your project directory to the path
project_home = '/home/YOUR_USERNAME/DATARADAR'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv(os.path.join(project_home, '.env'))

# Import the Flask app
from app_pythonanywhere import app as application
