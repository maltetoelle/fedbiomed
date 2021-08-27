import inspect
from joblib import dump, load
import numpy as np
from sklearn.linear_model import SGDRegressor, SGDClassifier, Perceptron
from sklearn.naive_bayes import BernoulliNB, GaussianNB
import json

class SGDSkLearnModel():
    '''Initialize model parameters'''
    def set_init_params(self, kwargs):
        if self.model_type in ['SGDRegressor']:
            self.param_list = ['intercept_','coef_']
            init_params = {'intercept_': np.array([0.]), 
                           'coef_':  np.array([0.]*kwargs['n_features'])}
        elif self.model_type in ['Perceptron', 'SGDClassifier']:
            self.param_list = ['intercept_','coef_']
            init_params = {'intercept_': np.array([0.]) if (kwargs['n_classes'] == 2) else np.array([0.]*kwargs['n_classes']),
                           'coef_':  np.array([0.]*kwargs['n_features']).reshape(1,kwargs['n_features']) if (kwargs['n_classes'] == 2) else np.array([0.]*kwargs['n_classes']*kwargs['n_features']).reshape(kwargs['n_classes'],kwargs['n_features'])  }

        for p in self.param_list:
            setattr(self.m, p, init_params[p])

    ''' Provide partial fit method of scikit learning model here. '''
    def partial_fit(self,X,y):
        pass

    '''Perform in this method all data reading and data transformations you need.
    At the end you should provide a couple (X,y) as indicated in the partial_fit
    method of the scikit learn class.'''
    def training_data(self, batch_size=None):
        pass

    ''' Provide a dictionnary with the parameters you need to be fitted, refer to
     scikit documentation for a detail of parameters '''
    def after_training_params(self):
        return {key: getattr(self.m, key) for key in self.param_list}

    '''
    Method training_routine called in Round, to change only if you know what you are doing.
    '''
    def training_routine(self, epochs=1, log_interval=10, lr=1e-3, batch_size=50, batch_maxnum=0, dry_run=False,
                         logger=None):
        print('SGD Regressor training batch size ', batch_size)
        #print('Init parameters', self.m.coef_, self.m.intercept_)
        (data, target) = self.training_data(batch_size=batch_size)
        for r in range(epochs):
            # do not take into account more than batch_maxnum batches from the dataset
            if batch_maxnum == 0 :
                if self.model_type == 'MultinomialNB' or self.model_type == 'BernoulliNB' or self.model_type == 'Perceptron' or self.model_type == 'SGDClassifier' or self.model_type == 'PassiveAggressiveClassifier' :
                    self.m.partial_fit(data,target, classes = np.unique(target))
                elif self.model_type == 'SGDRegressor' or self.model_type == 'PassiveAggressiveRegressor':
                    self.m.partial_fit(data,target)
                elif self.model_type == 'MiniBatchKMeans' or self.model_type == 'MiniBatchDictionaryLearning':
                    self.m.partial_fit(data)
            else:
                print('Not yet implemented batch_maxnum != 0')

        #print('MODEL PARAMS:',self.m.coef_, self.m.intercept_)

    def __init__(self,kwargs):
        self.batch_size = 100
        self.model_map = {'MultinomialNB', 'BernoulliNB', 'Perceptron', 'SGDClassifier', 'PassiveAggressiveClassifier',
                          'SGDRegressor', 'PassiveAggressiveRegressor', 'MiniBatchKMeans',
                          'MiniBatchDictionaryLearning'}

        self.dependencies = [   "from fedbiomed.common.fedbiosklearn import SGDSkLearnModel",
                                "import inspect",
                                "import pickle",
                                "import numpy as np",
                                "import pandas as pd",
                             ]
        if kwargs['model'] not in self.model_map:
            print('model must be one of, ', self.model_map)
        else:
            self.model_type = kwargs['model']
            self.m = eval(self.model_type)()
            self.params_sgd = self.m.get_params()
            from_kwargs_sgd_proper_pars = {key: kwargs[key] for key in kwargs if key in self.params_sgd}
            self.params_sgd.update(from_kwargs_sgd_proper_pars)
            self.param_list = []
            self.set_init_params(kwargs)
            self.dataset_path = None


    # provided by fedbiomed // necessary to save the model code into a file
    def add_dependency(self, dep):
        self.dependencies.extend(dep)
        pass

    '''Save the code to send to nodes '''
    def save_code(self, filename: str):
        """Save the class code for this training plan to a file
                Args:
                    filename (string): path to the destination file

                Returns:
                    None

                Exceptions:
                    none
        """
        content = ""
        for s in self.dependencies:
            content += s + "\n"

        content += "\n"
        content += inspect.getsource(self.__class__)

        # try/except todo
        file = open(filename, "w")
        file.write(content)
        file.close()

    ''' Save method for parameter communication, internally is used
    dump and load joblib library methods '''
    def save(self, filename, params: dict=None):
        '''
        Save can be called from Job or Round.
            From round is always called with params.
            From job is called with no params in constructor and
            with params in update_parameters.

            Torch state_dict has a model_params object. model_params tag
            is used in the code. This is why this tag is
            used in sklearn case.
        '''
        file = open(filename, "wb")
        if params is None:
            dump(self.m, file)
        else:
            if params.get('model_params') is not None: # called in the Round
                for p in params['model_params'].keys():
                    setattr(self.m, p, params['model_params'][p])
            else:
                for p in params.keys():
                    setattr(self.m, p, params[p])
            dump(self.m, file)
        file.close()

    ''' Save method for parameter communication, internally is used
        dump and load joblib library methods '''
    def load(self, filename, to_params: bool = False):
        '''
        Load can be called from Job or Round.
            From round is called with no params
            From job is called with  params
        '''
        di_ret = {}
        file = open( filename , "rb")
        if not to_params:
            self.m = load(file)
            di_ret =  self.m
        else:
            self.m =  load(file)
            di_ret['model_params'] = {key: getattr(self.m, key) for key in self.param_list}
        file.close()
        return di_ret

    # provided by the fedbiomed / can be overloaded // need WORK
    def logger(self, msg, batch_index, log_interval = 10):
        pass

    # provided by the fedbiomed // should be moved in a DATA manipulation module
    def set_dataset(self, dataset_path):
        self.dataset_path = dataset_path
        print('Dataset_path',self.dataset_path)

    def add_dependency(self, dep):
        self.dependencies.extend(dep)
        pass

    def get_model(self):
        return self.m

    def after_training_params(self):
        pass
