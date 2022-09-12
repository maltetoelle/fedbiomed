import os
import re
import uuid

from fedbiomed.common.exceptions import FedbiomedError
from app import app
from db import node_database
from flask import request, current_app
from middlewares import middleware, common
from schemas import AddDataSetRequest, \
    RemoveDatasetRequest, \
    UpdateDatasetRequest, \
    PreviewDatasetRequest, \
    AddDefaultDatasetRequest, \
    ListDatasetRequest, \
    GetCsvData, \
    ReadDataLoadingPlan
from utils import success, error, validate_request_data, response
from fedbiomed.common.data import MedicalFolderLoadingBlockTypes
from fedbiomed.node.dataset_manager import DatasetManager
from . import api

# Initialize Fed-BioMed DatasetManager
dataset_manager = DatasetManager()

DATA_PATH_RW = app.config['DATA_PATH_RW']


@api.route('/datasets/list', methods=['POST'])
@validate_request_data(schema=ListDatasetRequest)
def list_datasets():
    """
    List Datasets saved into Node DB

    Request.GET {None}:
        - No request data

    Response {application/json}:
        400:
            success   : Boolean error status (False)
            result  : null
            message : Message about error. Can be validation error or
                      error from TinyDBt
        200:
            success: Boolean value indicates that the request is success
            result: List of dataset objects
            endpoint: API endpoint
            message: The message for response
    """
    req = request.json
    search = req.get('search', None)
    table = node_database.table_datasets()
    query = node_database.query()

    if search is not None and search != "":
        res = table.search(query.name.search(search + '+') | query.description.search(search + '+'))
    else:
        try:
            res = table.all()
        except Exception as e:
            return error(str(e)), 400

    return response(res), 200


@api.route('/datasets/remove', methods=['POST'])
@validate_request_data(schema=RemoveDatasetRequest)
def remove_dataset():
    """ API endpoint to remove single dataset from database.
    This method removed dataset from database not from file system.

    Request {application/json}:
        dataset_id (str): Id of the dataset which will be removed

    Response {application/json}:
        400:
            success   : Boolean error status (False)
            result  : null
            message : Message about error. Can be validation error or
                      error from TinyDB
        200:
            success : Boolean value indicates that the request is success
            result  : null
            message : The message for response
    """
    req = request.json

    if req['dataset_id']:

        table = node_database.table_datasets()
        query = node_database.query()
        dataset = table.get(query.dataset_id == req['dataset_id'])

        if dataset:
            table.remove(doc_ids=[dataset.doc_id])
            return success('Dataset has been removed successfully'), 200

        else:
            return error('Can not find specified dataset in the database'), 400
    else:
        return error('Missing `dataset_id` attribute.'), 400


@api.route('/datasets/add', methods=['POST'])
@validate_request_data(schema=AddDataSetRequest)
@middleware(middlewares=[common.check_tags_already_registered])
def add_dataset():
    """ API endpoint to add single dataset to the database. Currently it
        uses some methods of data set manager.

    Request {application/json}:

        name (str): Name for the dataset
        tags (array): Tags for the dataset
        path (array): Data path where dataset is saved
        desc (string): Description for dataset
        type (string): Type of the dataset, CSV or Images

    Response {application/json}:
        400:
            error   : Boolean error status
            result  : null
            message : Message about error. Can be validation error or
                      error from TinyDB
        200:
            success : Boolean value indicates that the request is success
            result  : Dataset object (TindyDB doc).
            message : The message for response

    """
    table = node_database.table_datasets()
    query = node_database.query()

    data_path_rw = app.config['DATA_PATH_RW']
    req = request.json

    # Data path that the files will be read
    data_path = os.path.join(data_path_rw, *req['path'])

    # Data path that will be saved in the DB
    data_path_save = os.path.join(app.config['DATA_PATH_SAVE'], *req['path'])

    # Get image dataset information from data set manager
    if req['type'] == 'images':
        if not os.path.isdir(data_path):
            return error('Provided path is not a directory. Please select the folder that '
                         'includes sub folders of image dataset.'), 400
        try:
            shape = dataset_manager.load_images_dataset(data_path)
            types = []
        except Exception as e:
            return error(str(e)), 400
    # Get csv dataset information from dataset manager
    elif req['type'] == 'csv':
        accepted_ext = ['.csv', '.txt']
        extension = os.path.splitext(data_path)[1]
        if extension not in accepted_ext:
            return error(f'Unsupported extension "{extension}" for CSV datasets. '
                         f'Please select a "csv" or "txt" file.'), 400
        try:
            data = dataset_manager.load_csv_dataset(data_path)
            shape = data.shape
            types = dataset_manager.get_csv_data_types(data)
        except Exception as e:
            return error(str(e)), 400
    else:
        return error(f'Unknown dataset type "{req["type"]}"'), 400

    # Create unique id for the dataset
    dataset_id = 'dataset_' + str(uuid.uuid4())

    try:
        table.insert({
            "name": req['name'],
            "path": data_path_save,
            "data_type": req['type'],
            "dtypes": types,
            "shape": shape,
            "tags": req['tags'],
            "description": req['desc'],
            "dataset_id": dataset_id
        })
    except Exception as e:
        return error(str(e)), 400

    # Get saved dataset document
    res = table.get(query.dataset_id == dataset_id)

    return response(res), 200


@api.route('/datasets/update', methods=['POST'])
@validate_request_data(schema=UpdateDatasetRequest)
def update_dataset():
    """API endpoint for updating dataset

    ---
    Request {application/json}:
            name    : name for the dataset minLength:4 and MaxLength:124`
            tags    : new tags for the data sets
            desc    : String, description about dataset

    Response {application/json}:
        400:
            success : False, Boolean success status always, False
            result  : null
            message : Message about error. Can be validation error or
                      error from TinyDB

        200:
            success : Boolean value indicates that the request is success
            result  : Default dataset json object
            message : The message for response
    """
    req = request.json
    table = node_database.table_datasets()
    query = node_database.query()

    table.update({"tags": req["tags"],
                  "description": req["desc"],
                  "name": req["name"]},
                 query.dataset_id == req['dataset_id'])
    res = table.get(query.dataset_id == req['dataset_id'])

    return response(res), 200


@api.route('/datasets/preview', methods=['POST'])
@validate_request_data(schema=PreviewDatasetRequest)
def get_preview_dataset():
    """API endpoint for getting preview information for dataset
    ----
    Request {application/json}:
            dataset_id (str): ID of the dataset that will be
                              previewed

    Response {application/json}:
        400:
            error (bool): Boolean error status
            result (any): null
            message (str): Error message

        200:
            success (bool): Boolean value indicates that the request is success
            result (json): Default dataset json object
            endpoint (str): API endpoint
            message (str): The message for response
    """

    req = request.json
    table = node_database.table_datasets()
    query = node_database.query()
    dataset = table.get(query.dataset_id == req['dataset_id'])

    # Extract data path where the files are saved in the local repository
    rexp = re.match('^' + app.config['DATA_PATH_SAVE'], dataset['path'])
    data_path = dataset['path'].replace(rexp.group(0), app.config['DATA_PATH_RW'])

    if dataset:
        if os.path.isfile(data_path):
            df = dataset_manager.read_csv(data_path)
            data_preview = df.head().to_dict('split')
            dataset['data_preview'] = data_preview
        elif os.path.isdir(data_path):
            path_root = os.path.normpath(app.config["DATA_PATH_RW"]).split(os.sep)
            path = os.path.normpath(data_path).split(os.sep)
            dataset['data_preview'] = path[len(path_root):len(path)]
        else:
            dataset['data_preview'] = None

        matched = re.match('^' + app.config['NODE_FEDBIOMED_ROOT'], str(dataset['path']))
        if matched:
            dataset['path'] = dataset['path'].replace(app.config['NODE_FEDBIOMED_ROOT'], '$FEDBIOMED_DIR')

        return response(dataset), 200

    else:
        return error('No data has been found with this id'), 400


@api.route('/datasets/add-default-dataset', methods=['POST'])
@validate_request_data(schema=AddDefaultDatasetRequest)
def add_default_dataset():
    """API endpoint for adding default dataset

    ---

    Request {application/json}:
            name    : name of the default dataset, this parameter is not
                      required since the only default dataset is MNIST. Default value
                      is `mnist` that is generated by `AddDefaultDatasetRequest`

    Response {application/json}:
        400:
            error   : Boolean error status
            result  : null
            message : Message about error. For this API it comes from
                     `DatasetManager` class of Fed-BioMed.

        200:
            success : Boolean value indicates that the request is success
            result  : Default dataset json object
            endpoint: API endpoint
            message : The message for response

    """
    req = request.json
    table = node_database.table_datasets()
    query = node_database.query()
    dataset = table.get(query.tags == req['tags'])

    if dataset:
        return error(f'Default dataset has been already deployed with tags: {req["tags"]}'), 400

    if 'path' in req:
        # Data path that the files will be read
        path = os.path.join(app.config['DATA_PATH_RW'], *req['path'])
        # This is the path will be writen in DB
        data_path = os.path.join(app.config['DATA_PATH_SAVE'], *req['path'])
        if not os.path.isdir(path):
            return error('Provided path is not a directory. Please select a folder not a file.'), 400
    else:
        default_dir = os.path.join(app.config["DATA_PATH_RW"], 'defaults')
        path = os.path.join(default_dir, 'mnist')
        if not os.path.exists(default_dir):
            os.mkdir(default_dir)
        if not os.path.exists(os.path.join(default_dir, 'mnist')):
            os.mkdir(path)

        # This is the path will be writen in DB
        data_path = os.path.join(app.config['DATA_PATH_SAVE'], 'defaults', 'mnist')

    try:
        shape = dataset_manager.load_default_database(name="MNIST",
                                                      path=path,
                                                      as_dataset=False)
    except Exception as e:
        return error(str(e)), 400

    # Create unique id for the dataset
    dataset_id = 'dataset_' + str(uuid.uuid4())

    try:
        table.insert({
            "name": req['name'],
            "path": data_path,
            "data_type": 'default',
            "dtypes": [],
            "shape": shape,
            "tags": req['tags'],
            "description": req['desc'],
            "dataset_id": dataset_id})

    except Exception as e:
        return error(str(e)), 400

    res = table.get(query.dataset_id == dataset_id)

    return response(res), 200


@api.route('/datasets/get-csv-data', methods=['POST'])
@validate_request_data(schema=GetCsvData)
def get_csv_data():
    """
    Loads csv from given path

    """
    req = request.json

    # Data path that the files will be read
    data_path = os.path.join(DATA_PATH_RW, *req['path'])

    if not os.path.isfile(data_path):
        return error(f"Path does not correspond to a valid data file: {os.path.join(*req['path'])}"), 400

    try:
        df = dataset_manager.read_csv(data_path)
        rows = df.shape[0]
        df.fillna("NULL", inplace=True)
        data_preview = df.iloc[0:30, :].to_dict('split')
        data_preview.update({"samples": rows, "displays": 30})
    except Exception as e:
        return error(f"Can not read given data file please make sure the format "
                     f"is one of csv, tsv or txt: {e}"), 400

    return response(data_preview), 200


@api.route('/datasets/list-dlps', methods=['GET'])
def list_data_loading_plans():
    """List all DLPs in the database
    """
    dlps = dataset_manager.list_dlp()
    index = list(range(len(dlps)))
    columns = ['name', 'id']
    data = [[dlp['dlp_name'], dlp['dlp_id']] for dlp in dlps]

    return response({'index': index, 'columns': columns, 'data': data}), 200


@api.route('/datasets/read-dlp', methods=['POST'])
@validate_request_data(schema=ReadDataLoadingPlan)
def read_data_loading_plans():
    """Read content of a specified DLP
    """
    req = request.json
    data_dlp = {}

    try:
        dlp, dlbs = dataset_manager.get_dlp_by_id(req['dlp_id'])
    except FedbiomedError as e:
        return error(f"Could not read customizations: {e}"), 400

    m2f = MedicalFolderLoadingBlockTypes.MODALITIES_TO_FOLDERS.value
    if 'loading_blocks' in dlp and m2f in dlp['loading_blocks']:
        dlb_id_m2f = dlp['loading_blocks'][m2f]
        map = [dlb['map'] for dlb in dlbs if dlb['loading_block_serialization_id'] == dlb_id_m2f]
        if len(map) != 1:
            return error("Could not read customizations: database coherence error"), 400
        data_dlp['map'] = map[0]

    return response(data_dlp), 200
