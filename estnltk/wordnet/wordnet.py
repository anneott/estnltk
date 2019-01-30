import sqlite3
import os.path

class WordnetException(Exception):
    pass


class Wordnet:

    '''
    Wordnet class which implements sqlite database connection.
    '''

    def __init__(self, version='74'):
        self.conn = None
        self.cur = None
        self.version = version

        wn_dir = '{}/data/estwn_kb{}'.format(os.path.dirname(os.path.abspath(__file__)), self.version)
        wn_entry = '{}/wordnet_entry.db'.format(wn_dir)
        wn_relation = '{}/wordnet_relation.db'.format(wn_dir)

        if not os.path.exists(wn_dir):
            raise WordnetException("Invalid wordnet version: \n\tmissing directory: {}".format(wn_dir))
        if not os.path.exists(wn_entry):
            raise WordnetException("Invalid wordnet version: \n\tmissing file: {}".format(wn_entry))
        if not os.path.exists(wn_relation):
            raise WordnetException("Invalid wordnet version: \n\tmissing file: {}".format(wn_relation))

        try: 
            self.conn = sqlite3.connect(wn_entry)
            self.cur = self.conn.cursor()
            self.conn.execute("ATTACH DATABASE '{}' AS wordnet_relation".format(wn_relation))

        except sqlite3.OperationalError as e:
            raise WordnetException("Invalid wordnet file: \n\tsqlite connection error: {}".format(e))

        except Exception as e:
            raise WordnetException("Unexpected error: \n\t{}: {}".format(type(e), e))

    def __del__(self):
        self.conn.close()
        
    def get_synset(self, synset_id):
    
        with self.conn:
            self.cur.execute('''SELECT literal FROM wordnet_entry WHERE id = {} ''' .format(synset_id))
            return [row[0] for row in self.cur.fetchall()]