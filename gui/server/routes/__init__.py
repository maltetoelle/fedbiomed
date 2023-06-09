from flask import Blueprint
from utils import error
from flask_jwt_extended import verify_jwt_in_request

# Create a blue print for `/api` url prefix. The URLS
api = Blueprint('api', __name__, url_prefix='/api')
auth = Blueprint('auth', __name__, url_prefix='/api/auth')


@api.before_request
def before_api_request():
    try:
        verify_jwt_in_request()
    except Exception as e:
        return error('Invalid token'), 401

# Uses api/ prefix for API endpoints
from .authentication import *
from .config import *
from .datasets import *
from .repository import *
from .medical_folder_dataset import *
from .model import *
from .users import *

