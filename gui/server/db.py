from datetime import datetime
from typing import Dict
import uuid
#from fedbiomed.common.constants import UserRoleType
from tinydb import TinyDB, Query
from tinydb.table import Table

from app import app, config
from utils import set_password_hash

class BaseDatabase:

    def __init__(self, db_path: str):
        """ Database class for TinyDB. It is general wrapper for
            TinyDB. It can be extended in the future, if Fed-BioMed
            support a=other persistent databases.
        """
        self._db = TinyDB(db_path)
        self._query = Query()

    def query(self):
        return self._query

    def _table(self, name: str) -> Table:
        """ Method for selecting table

        Args:

            name    (str): Table name.

        Returns:
            A TinyDB `Table` object for the selected table.
        """

        if self._db is None:
            raise Exception('Please initialize database first')

        # don't use read cache to avoid coherence problems
        return self._db.table(name=name, cache_size=0)


class NodeDatabase(BaseDatabase):

    def __init__(self, db_path: str):
        super(NodeDatabase, self).__init__(db_path)

    def table_datasets(self) -> Table:
        """Method  for selecting TinyDB table containing the datasets.

        Returns:
            A TinyDB `Table` object for this table. 
        """
        return self._table('Datasets')


class UserDatabase(BaseDatabase):

    def __init__(self, db_path: str):
        super(UserDatabase, self).__init__(db_path)

    def table_users(self) -> Table:
        """Method  for selecting TinyDB table containing the datasets.

        Returns:
            A TinyDB `Table` object for this table.
        """
        return self._table('Users')

    def add_default_admin_user(self, admin_credential: Dict[str, str]):
        """adds default admin user to database if no admin has been found in database"""
        # TODO: check if there is no admin registered in database
        email, password = admin_credential['email'], admin_credential['password']
        try:

            self.table_users().insert({"user_email": email,
                "password_hash": set_password_hash(password),
                "user_role": 1, # figure out a way to do that with UserRoleType
                "creation_date": datetime.utcnow().ctime(),
                "user_id": 'user_' + str(uuid.uuid4())})
        except Exception as e:
            print(f"error, unable to add default admin account to database {e}")


node_database = NodeDatabase(app.config['NODE_DB_PATH'])
user_database = UserDatabase(app.config['GUI_DB_PATH'])
user_database.add_default_admin_user(config.configuration['DEFAULT_ADMIN_CREDENTIAL'])
