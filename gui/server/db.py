from app import app
from tinydb import TinyDB, Query


class Database:

    def __init__(self, name: str):
        """ Database class for TinyDB. It is general wrapper for
            TinyDB. It can be extended in the future, if Fed-BioMed
            support a=other persistent databases.
        """
        self._db = TinyDB(name)
        self._query = Query()

    def db(self):
        """ Getter for db """

        return self

    def query(self):
        return self._query

    def table(self, name: str = '_default'):
        """ Method for selecting table 

        Args: 

            name    (str): Table name. Default is `_default`
                            when there is no table specified TinyDB
                            write data into `_default` table
        """

        if self._db is None:
            raise Exception('Please initialize database first')

        return self._db.table(name)

    def close(self):
        """This method removes TinyDB object to save some memory"""

        self._db.close()


node_database = Database(app.config['NODE_DB_PATH'])
gui_database = Database(app.config['GUI_DB_PATH'])
