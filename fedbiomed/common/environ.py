'''
al environment/configuration variables are provided by the
**Environ** dictionnary. **Environ** is a singleton class,
meaning that only an instance of Environ is available.
'''


import configparser
import os
import uuid

from fedbiomed.common.constants      import ErrorNumbers
from fedbiomed.common.exceptions     import FedbiomedEnvironError
from fedbiomed.common.logger         import logger
from fedbiomed.common.singleton      import SingletonMeta
from fedbiomed.common.constants      import ComponentType, HashingAlgorithms


"""
Descriptions of global/environment variables

Resarcher Global Variables:
    RESEARCHER_ID           : id of the researcher
    ID                      : equals to researcher id
    TENSORBOARD_RESULTS_DIR : path for writing tensorboard log files
    EXPERIMENTS_DIR         : folder for saving experiments
    MESSAGES_QUEUE_DIR      : Path for writing queue files

Nodes Global Variables:
    NODE_ID                 : id of the node
    ID                      : equals to node id
    MESSAGES_QUEUE_DIR      : Path for queues
    DB_PATH                 : TinyDB database path where datasets are saved
    MODEL_DB_PATH           : Database where registered model are saved
    
Common Global Variables:
    COMPONENT_TYPE          : Node or Researcher
    CONFIG_DIR              : Configuration file path
    VAR_DIR                 : Var directory of Fed-Biomed
    CACHE_DIR               : Cache directory of Fed-BioMed
    TMP_DIR                 : Temporary directory
    MQTT_BROKER             : MQTT broker IP address
    MQTT_BROKER_PORT        : MQTT broker port
    UPLOADS_URL             : Upload URL for file repository
    TRAINING_PLAN           : Type of Training Plan
"""


class Environ(metaclass = SingletonMeta):
    """
    this (singleton) class contains all variables for researcher or node
    """

    def __init__(self, component: ComponentType = None, rootdir: str = None):
        """
        class constructor

        input:
        - type of the component either ComponentType.NODE or ComponentType.RESEARCHER
        - root directory: if not provided the rootdirectory is deduced from the package location
          (mainly used by the test files)

        raises FedbiomedEnvironError is component type is wrong
        """
        # dict with contains all configuration values
        self._values = {}

        if component == ComponentType.NODE or component == ComponentType.RESEARCHER :
            self._values['COMPONENT_TYPE'] = component
        else:
            _msg = ErrorNumbers.FB600.value + ": parameter should be of ComponentType"
            logger.critical(_msg)
            raise FedbiomedEnvironError(_msg)

        # common values for all components
        self._init_common( rootdir = rootdir)

        # specific configuration values
        if component == ComponentType.RESEARCHER:
            logger.setLevel("DEBUG")
            self._init_researcher()

        if component == ComponentType.NODE:
            logger.setLevel("INFO")
            self._init_node()

        # display some information on the present environment
        self.info()


    def __getitem__(self, key: str):
        """
        override the [] get operator to control the Exception type

        raises FedbiomedEnvironError if key does not exists
        """
        if key not in self._values:
            _msg = ErrorNumbers.FB600.value + ": config file doe not contain the key: " + str(key)
            logger.critical(_msg)
            raise FedbiomedEnvironError(_msg)
        return self._values[key]


    def __setitem__(self, key: str, value):
        """
        override the [] set operator to control the Exception type

        raises FedbiomedEnvironError is key does not exists
        """

        if value is None:
            _msg = ErrorNumbers.FB600.value + ": cannot set value to None for key: " + str(key)
            logger.critical(_msg)
            raise FedbiomedEnvironError(_msg)

        self._values[key] = value
        return value


    def _init_common(self, rootdir):
        """
        common configuration values for researcher and node

        raises FedbiomedEnvironError in case of error (OS errors usually)
        """

        # guess the fedbiomed package topir if no rootdir is given
        if rootdir is None:
            # locate the top dir from the file location (got up twice)
            ROOT_DIR = os.path.abspath(
                os.path.join(
                    os.path.dirname(
                        os.path.abspath(__file__)),
                    '..',
                    '..'
                )
            )
        else:
            ROOT_DIR = rootdir

        # Initialize TRAINING_PLAN STATUS
        self._values['TRAINING_PLAN'] = None

        # Initialize all environment values
        self._values['ROOT_DIR'] = ROOT_DIR

        # main directories
        self._values['CONFIG_DIR'] = os.path.join(ROOT_DIR, 'etc')
        VAR_DIR = os.path.join(ROOT_DIR, 'var')
        self._values['VAR_DIR']    = VAR_DIR
        self._values['CACHE_DIR']  = os.path.join(VAR_DIR, 'cache')
        self._values['TMP_DIR']    = os.path.join(VAR_DIR, 'tmp')

        for _key in 'CONFIG_DIR', 'VAR_DIR', 'CACHE_DIR', 'TMP_DIR':
            dir = self._values[_key]
            if not os.path.isdir(dir):
                try:
                    os.makedirs(dir)
                except FileExistsError:
                    _msg = ErrorNumbers.FB600.value + ": path already exists but is not a directory: " + dir
                    logger.critical(_msg)
                    raise FedbiomedEnvironError(_msg)
                except OSError:
                    _msg = ErrorNumbers.FB600.value + ": cannot create environment subtree in: " + dir
                    logger.critical(_msg)
                    raise FedbiomedEnvironError(_msg)

        pass


    def _init_researcher(self):
        """
        specific configuration values for researcher

        raises FedbiomedEnvironError:
        - if file parser cannot be instanciated
        - in case of file system errors (cannot create experiment directories)
        """
        # Parse config file
        cfg = self._parse_config_file()

        # Initialize network configurations for Researcher component
        self._init_network_configurations(cfg)


        # we may remove RESEARCHER_ID in the future (to simplify the code)
        # and use ID instead
        try:
            _cfg_value = cfg.get('default', 'researcher_id')
        except configparser.Error:
            _msg = ErrorNumbers.FB600.value + \
                ": no default/researcher_id in config file, please recreate a new config file"
            logger.critical(_msg)
            raise FedbiomedEnvironError(_msg)

        self._values['RESEARCHER_ID'] = os.getenv('RESEARCHER_ID',
                                                  _cfg_value)
        self._values['ID'] = self._values['RESEARCHER_ID']


        ROOT_DIR = self._values['ROOT_DIR']
        VAR_DIR = self._values['VAR_DIR']

        # more directories
        self._values['TENSORBOARD_RESULTS_DIR'] = os.path.join(ROOT_DIR, 'runs')
        self._values['EXPERIMENTS_DIR'] = os.path.join(VAR_DIR, "experiments")

        for _key in 'TENSORBOARD_RESULTS_DIR', 'EXPERIMENTS_DIR':
            dir = self._values[_key]
            if not os.path.isdir(dir):
                try:
                    os.makedirs(dir)
                except FileExistsError:
                    _msg = ErrorNumbers.FB600.value + ": path already exists but is not a directory " + dir
                    logger.critical(_msg)
                    raise FedbiomedEnvironError(_msg)
                except OSError:
                    _msg = ErrorNumbers.FB600.value + ": cannot create environment subtree in: " + dir
                    logger.critical(_msg)
                    raise FedbiomedEnvironError(_msg)

        self._values['MESSAGES_QUEUE_DIR'] = os.path.join( VAR_DIR, 'queue_messages')

        pass

    def _init_node(self):
        """
        specific configuration values for node

        raises FedbiomedEnvironError:
        - if file parser cannot be instanciated
        - in case of missing keys in the config file
        """

        # Parse config file
        cfg = self._parse_config_file()
        self._init_network_configurations(cfg)

        try:
            _cfg_value = cfg.get('default', 'node_id')
        except configparser.Error:
            _msg = ErrorNumbers.FB600.value + ": no default/node_id in config file, please recreate a new config file"
            logger.critical(_msg)
            raise FedbiomedEnvironError(_msg)

        self._values['NODE_ID']   = os.getenv('NODE_ID', _cfg_value)
        self._values['ID']        = self._values['NODE_ID']


        VAR_DIR = self._values['VAR_DIR']
        NODE_ID = self._values['NODE_ID']
        ROOT_DIR = self._values['ROOT_DIR']

        self._values['MESSAGES_QUEUE_DIR']  = os.path.join(VAR_DIR,
                                                           f'queue_manager_{NODE_ID}')
        self._values['DB_PATH']             = os.path.join(VAR_DIR,
                                                           f'db_{NODE_ID}.json')

        self._values['DEFAULT_MODELS_DIR']  = os.path.join(ROOT_DIR,
                                                           'envs' , 'development', 'default_models')

        try:
            _cfg_value = cfg.get('security', 'allow_default_models')
        except configparser.Error:
            _msg = ErrorNumbers.FB600.value + \
                ": no security/allow_default_models in config file, please recreate a new config file"
            logger.critical(_msg)
            raise FedbiomedEnvironError(_msg)

        self._values['ALLOW_DEFAULT_MODELS'] = os.getenv('ALLOW_DEFAULT_MODELS',
                                                         _cfg_value) \
                                                 .lower() in ('true', '1', 't', True)

        try:
            _cfg_value = cfg.get('security', 'model_approval')
        except configparser.Error:
            _msg = ErrorNumbers.FB600.value + \
                ": no security/model_approval in config file, please recreate a new config file"
            logger.critical(_msg)
            raise FedbiomedEnvironError(_msg)

        self._values['MODEL_APPROVAL'] = os.getenv('ENABLE_MODEL_APPROVAL',
                                                   _cfg_value) \
                                           .lower() in ('true', '1', 't', True)

        try:
            _cfg_value = cfg.get('security', 'hashing_algorithm')
        except configparser.Error:
            _msg = ErrorNumbers.FB600.value + \
                ": no security/hashing_algorithm in config file, please recreate a new config file"
            logger.critical(_msg)
            raise FedbiomedEnvironError(_msg)

        hashing_algorithm = _cfg_value

        if hashing_algorithm in HashingAlgorithms.list():
            self._values['HASHING_ALGORITHM'] = hashing_algorithm
        else:
            _msg = ErrorNumbers.FB600.value + ": unknown hashing algorithm: " + str(hashing_algorithm)
            logger.critical(_msg)
            raise FedbiomedEnvironError(_msg)


        # ========= PATCH MNIST Bug torchvision 0.9.0 ===================
        # https://github.com/pytorch/vision/issues/1938

        # imported only for the node component
        from six.moves import urllib

        opener = urllib.request.build_opener()
        opener.addheaders = [
            ('User-agent', 'Python-urllib/3.7'),
            ('Accept',
             'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8'),
            ('Accept-Language', 'en-US,en;q=0.9'),
            ('Accept-Encoding', 'gzip, deflate, br')
        ]
        urllib.request.install_opener(opener)

        pass

    def _parse_config_file(self):
        """ Read the .ini file corresponding to the component
        create the file with default values if it does not exists.
        Complete/modify the environment with values coming from the
        OS environment variables
        """

        # Get config file, it create new config if there is not any
        # get config file location from environment
        # or use a predefined value
        if os.getenv('CONFIG_FILE') :
            CONFIG_FILE = os.getenv('CONFIG_FILE')
            if not os.path.isabs(CONFIG_FILE):
                CONFIG_FILE = os.path.join(self._values['CONFIG_DIR'],
                                           os.getenv('CONFIG_FILE'))
        else:
            if self._values['COMPONENT_TYPE'] == ComponentType.RESEARCHER:
                CONFIG_FILE = os.path.join(self._values['CONFIG_DIR'],
                                           'config_researcher.ini')
            else:
                CONFIG_FILE = os.path.join(self._values['CONFIG_DIR'],
                                           'config_node.ini')


        # Parser for the .ini file
        try:
            cfg = configparser.ConfigParser()
        except configparser.Error:
            _msg = ErrorNumbers.FB600.value + ": cannot parse configuration file"
            logger.critical(_msg)
            raise FedbiomedEnvironError(_msg)

        if os.path.isfile(CONFIG_FILE):
            # get values from .ini file
            try:
                cfg.read(CONFIG_FILE)
            except configparser.Error:
                _msg = ErrorNumbers.FB600.value + ": cannot read config file, check file permissions"
                logger.critical(_msg)
                raise FedbiomedEnvironError(_msg)

        else:
            if self._values['COMPONENT_TYPE'] == ComponentType.RESEARCHER:
                self._create_researcher_config_file(cfg, CONFIG_FILE)
            else:
                self._create_node_config_file(cfg, CONFIG_FILE)


        # store the CONFIG_FILE in environ (may help to debug)
        self._values['CONFIG_FILE'] = CONFIG_FILE

        return cfg

    def _create_node_config_file(self, cfg, config_file):
        """
        Creates new config file for node

        Args:
            config_file (str): The path indicated where config file
                               should be saved.

        """

        # get uploads url
        uploads_url = self._get_uploads_url()


        # TODO: We may remove node_id in the future (to simplify the code)
        node_id = os.getenv('NODE_ID', 'node_' + str(uuid.uuid4()))

        cfg['default'] = {
            'node_id': node_id,
            'uploads_url': uploads_url
        }


        # Message broker
        mqtt_broker = os.getenv('MQTT_BROKER', 'localhost')
        mqtt_broker_port = int(os.getenv('MQTT_BROKER_PORT', 1883))

        cfg['mqtt'] = {
            'broker_ip': mqtt_broker,
            'port': mqtt_broker_port,
            'keep_alive': 60
        }

        # Security variables
        # Default hashing algorithim is SHA256
        allow_default_models = os.getenv('ALLOW_DEFAULT_MODELS' , True)
        model_approval = os.getenv('ENABLE_MODEL_APPROVAL' , False)

        cfg['security'] = {
            'hashing_algorithm': HashingAlgorithms.SHA256.value,
            'allow_default_models': allow_default_models,
            'model_approval': model_approval
        }


        # write the config for future relaunch of the same component
        # (only if the file does not exists)
        try:
            with open(config_file, 'w') as f:
                cfg.write(f)
        except configparser.Error:
            _msg = ErrorNumbers.FB600.value + ": cannot save config file: " + config_file
            logger.critical(_msg)
            raise FedbiomedEnvironError(_msg)

        pass

    def _create_researcher_config_file(self, cfg, config_file):
        """
        Create config file for researcher

        raises FedbiomedEnvironError is config file cannot be created
        """

        # get uploads url
        uploads_url = self._get_uploads_url()

        # Default configuration
        researcher_id = os.getenv('RESEARCHER_ID', 'researcher_' + str(uuid.uuid4()))
        cfg['default'] = {
            'researcher_id': researcher_id,
            'uploads_url': uploads_url
        }


        # Message broker
        mqtt_broker = os.getenv('MQTT_BROKER', 'localhost')
        mqtt_broker_port = int(os.getenv('MQTT_BROKER_PORT', 1883))

        cfg['mqtt'] = {
            'broker_ip': mqtt_broker,
            'port': mqtt_broker_port,
            'keep_alive': 60
        }

        # write the config for future relaunch of the same component
        # (only if the file does not exists)
        try:
            with open(config_file, 'w') as f:
                cfg.write(f)
        except configparser.Error:
            _msg = ErrorNumbers.FB600.value + ": cannot save config file: " + config_file
            logger.critical(_msg)
            raise FedbiomedEnvironError(_msg)


    def _init_network_configurations(self, cfg):
        """
        Initialize network configurations

        raises FedbiomedEnvironError in case of missing keys/values
        """

        # broker location
        try:
            _cfg_value = cfg.get('mqtt', 'broker_ip')
        except configparser.Error:
            _msg = ErrorNumbers.FB600.value + ": no mqtt/broker_ip in config file, please recreate a new config file"
            logger.critical(_msg)
            raise FedbiomedEnvironError(_msg)

        self._values['MQTT_BROKER'] = os.getenv('MQTT_BROKER',
                                                _cfg_value)

        try:
            _cfg_value = cfg.get('mqtt', 'port')
        except configparser.Error:
            _msg = ErrorNumbers.FB600.value + ": no mqtt/port in config file, please recreate a new config file"
            logger.critical(_msg)
            raise FedbiomedEnvironError(_msg)

        self._values['MQTT_BROKER_PORT']  = int(os.getenv('MQTT_BROKER_PORT',
                                                          _cfg_value))

        # repository location
        try:
            _cfg_value = cfg.get('default', 'uploads_url')
        except configparser.Error:
            _msg = ErrorNumbers.FB600.value + \
                ": no default/uploads_url in config file, please recreate a new config file"
            logger.critical(_msg)
            raise FedbiomedEnvironError(_msg)

        UPLOADS_URL = _cfg_value
        uploads_ip = os.getenv('UPLOADS_IP')
        if uploads_ip:
            UPLOADS_URL = "http://" + uploads_ip + ":8844/upload/"
            UPLOADS_URL = os.getenv('UPLOADS_URL', UPLOADS_URL)

        # trailing slash is needed for repo url
        if not UPLOADS_URL.endswith('/'):
            UPLOADS_URL += '/'

        self._values['UPLOADS_URL'] = UPLOADS_URL
        self._values['TIMEOUT']     = 5

    @staticmethod
    def _get_uploads_url():
        """
        Gets uploads url from env
        """

        # use default values from current OS environment variables
        # repository location
        uploads_url = "http://localhost:8844/upload/"
        uploads_ip = os.getenv('UPLOADS_IP')
        if uploads_ip:
            uploads_url = "http://" + uploads_ip + ":8844/upload/"
        uploads_url = os.getenv('UPLOADS_URL', uploads_url)

        return uploads_url

    def info(self):
        """
        Print useful information at environment creation
        """

        logger.info("Component environment:")
        if self._values['COMPONENT_TYPE'] == ComponentType.RESEARCHER:
            logger.info("type = " + str(self._values['COMPONENT_TYPE']))

        if self._values['COMPONENT_TYPE'] == ComponentType.NODE:
            logger.info("type                = " + str(self._values['COMPONENT_TYPE']))
            logger.info("model_approval      = " + str(self._values['MODEL_APPROVAL']))
            logger.info("allow_default_model = " + str(self._values['ALLOW_DEFAULT_MODELS']))
