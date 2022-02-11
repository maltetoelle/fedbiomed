# Managing NODE, RESEARCHER environ mock before running tests
import shutil

from testsupport.delete_environ import delete_environ

# Delete environ. It is necessary to rebuild environ for required component
delete_environ()
# overload with fake environ for tests
import testsupport.mock_common_environ
# Import environ for researcher, since tests will be running for researcher component
from fedbiomed.researcher.environ import environ

import os
import inspect
import unittest
from unittest.mock import patch, MagicMock

import torch
import numpy as np

from fedbiomed.researcher.job import Job
from fedbiomed.researcher.responses import Responses
from testsupport.fake_responses import FakeResponses
from testsupport.fake_model import FakeModel
from fedbiomed.researcher.requests import Requests
from fedbiomed.common.torchnn import TorchTrainingPlan


class TestJob(unittest.TestCase):

    @classmethod
    def create_fake_model(cls, name: str):
        """ Class method saving codes of FakeModel

        Args:
            name (str): Name of the model file that will be created
        """

        tmp_dir = os.path.join(environ['TMP_DIR'], 'tmp_models')
        tmp_dir_model = os.path.join(tmp_dir, name)
        os.mkdir(tmp_dir)
        content = inspect.getsource(FakeModel)
        file = open(tmp_dir_model, "w")
        file.write(content)
        file.close()

        return tmp_dir_model

    # once in test lifetime
    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):

        self.patcher = patch('fedbiomed.researcher.requests.Requests.__init__',
                             return_value=None)
        self.patcher2 = patch('fedbiomed.common.repository.Repository.upload_file',
                              return_value={"file": environ['UPLOADS_URL']})
        self.mock_reqeust = self.patcher.start()
        self.mock_upload_file = self.patcher2.start()

        # Globally create mock for Model and FederatedDataset
        self.model = MagicMock(return_value=None)
        self.model.save = MagicMock(return_value=None)
        self.model.save_code = MagicMock(return_value=None)

        self.fds = MagicMock()
        self.fds.data = MagicMock(return_value={})
        # ----------------------------------------------------

    def tearDown(self) -> None:

        self.patcher.stop()
        self.patcher2.stop()
        # shutil.rmtree(os.path.join(VAR_DIR, "breakpoints"))
        # (above) remove files created during these unit tests

        # Remove if there is dummy model file
        tmp_dir = os.path.join(environ['TMP_DIR'], 'tmp_models')
        if os.path.isdir(tmp_dir):
            shutil.rmtree(tmp_dir)

    # tests
    def test_job(self):
        '''

        '''
        # does not work yet !!
        # j = Job()

        pass

    @patch('fedbiomed.common.logger.logger.critical')
    def test_job_01_init_t1(self,
                            mock_logger_critical):
        """ Test first raise error when there is no model provided """
        mock_logger_critical.return_value = None

        with self.assertRaises(NameError):
            j = Job()
            mock_logger_critical.assert_called_once()

    def test_job_02_init_keep_files_dir(self):
        """ Testing initialization of Job with keep_files_dir """

        j = Job(model=self.model,
                data=self.fds,
                keep_files_dir=environ['TMP_DIR'])

        # Check keep files dir properly set
        self.assertEqual(j._keep_files_dir, environ['TMP_DIR'], 'keep_files_dir does not matched given path')

    def test_job_03_init_provide_reqeust(self):
        """ Testing initialization of Job by providing Request object """

        reqs = Requests()
        j = Job(model=self.model,
                data=self.fds,
                reqs=reqs)

        self.assertEqual(j._reqs, reqs, 'Job did not initialize provided Reqeust object')

    def test_job_02_init_building_model_from_path(self):

        """ Test model is passed as static python file with model_path """

        # Get source of the model and save in tmp directory for just test purposes
        tmp_dir_model = TestJob.create_fake_model('fake_model.py')

        j = Job(model_path=tmp_dir_model,
                model='FakeModel')

        self.assertEqual(j.model_instance.__class__.__name__, FakeModel.__name__,
                         'Provided model and model instance of Job do not match, '
                         'while initializing Job with static model python file')

        self.assertEqual(j._model_class, 'FakeModel',
                         'Model is not initialized properly while providing model_path')

        # Upload file must be called 2 times one for model
        # another one for initial model parameters
        self.assertEqual(self.mock_upload_file.call_count, 2)

    @patch('fedbiomed.common.logger.logger.critical')
    def test_job_init_03_build_wrongly_saved_model(self, mock_logger_critical):
        """ Testing when model code saved with unsupported module name

            - This test will catch raise SystemExit
        """

        mock_logger_critical.return_value = None

        # Save model with unsupported module name
        tmp_dir_model = TestJob.create_fake_model('fake-model.py')

        with self.assertRaises(SystemExit):
            j = Job(model_path=tmp_dir_model,
                    model='FakeModel')
            mock_logger_critical.assert_called_once()

    @patch('fedbiomed.common.logger.logger.critical')
    @patch('inspect.isclass')
    def test_job_04_init_isclass_raises_error(self,
                                              mock_isclass,
                                              mock_logger_critical):
        """ Test initialization when inspect.isclass raises NameError"""

        mock_isclass.side_effect = NameError
        with self.assertRaises(NameError):
            j = Job(model='FakeModel',
                    data=self.fds)
            mock_logger_critical.assert_called_once()

    def test_job_05_initialization_with_model_arguments(self):
        """ Test building model with model arguments during init of Job"""

        model_args = {"test": "test"}

        j = Job(model=FakeModel,
                data=self.fds,
                model_args=model_args)

        # Check model has been called with correct arguments
        self.assertDictEqual(j.model_instance.model_args, model_args,
                             'Model arguments has not been instantiated properly')

    @patch('fedbiomed.common.logger.logger.error')
    def test_job_05_initialization_raising_exception_save_and_save_code(self,
                                                                        mock_logger_error):

        """ Test Job initialization when model_instance.save and save_code raises Exception """

        mock_logger_error.return_values = None

        # Test TRY/EXCEPT when save_code raises Exception
        self.model.save_code.side_effect = Exception
        j = Job(model=self.model, data=self.fds)
        mock_logger_error.assert_called_once()

        # Reset mocks for next tests
        self.model.save_code.side_effect = None
        mock_logger_error.reset_mock()

        # Test TRY/EXCEPT when model.save() raises Exception
        self.model.save.side_effect = Exception
        j = Job(model=self.model, data=self.fds)
        mock_logger_error.assert_called_once()

    def test_job_06_properties_setters(self):


        j = Job(model=self.model,
                data=self.fds)

        self.assertEqual(self.model, j.model, 'Can not get Requests attribute from Job properly')
        self.assertEqual('MagicMock', j.model_class, 'Can not model class properly')
        self.assertEqual(j._reqs, j.requests, 'Can not get Requests attribute from Job properly')

        model_file = j.model_file
        self.assertEqual(model_file, j._model_file, 'model_file attribute of job is not got correctly')

        nodes = {'node-1': 1, 'node-2': 2}
        j.nodes = nodes
        self.assertDictEqual(nodes, j.nodes, 'Can not set or get properly nodes attribute of Job')

        tr = j.training_replies
        self.assertEqual(j._training_replies, tr, 'Can not get training_replies correctly')

        j.training_args = {'test': 'test'}
        targs = j.training_args
        self.assertDictEqual({'test': 'test'}, targs, 'Can not get or set training_args correctly')


    def test_job_01_save_private_training_replies(self):
        """
        tests if `_save_training_replies` is properly extracting
        breakpoint info from `training_replies`. It uses a dummy class
        FakeResponses, a weak implementation of `Responses` class
        """

        # instantiate job
        test_job = Job(model=self.model,
                       data=self.fds)

        # first create a `_training_replies` variable
        training_replies = {
            0: FakeResponses([]),
            1: FakeResponses(
                [
                    {
                        "node_id": '1234',
                        'params': torch.Tensor([1, 3, 5]),
                        'dataset_id': 'id_node_1'
                    },
                    {
                        "node_id": '5678',
                        'params': np.array([1, 3, 5]),
                        'dataset_id': 'id_node_2'
                    },
                ])
        }

        # action
        new_training_replies = test_job._save_training_replies(training_replies)

        # check if `training_replies` is  saved accordingly
        self.assertTrue(type(new_training_replies) is list)
        self.assertTrue(len(new_training_replies) == 2)
        self.assertTrue('params' not in new_training_replies[1][0])
        self.assertEqual(new_training_replies[1][1].get('dataset_id'), 'id_node_2')

    @patch('fedbiomed.researcher.responses.Responses.__getitem__')
    @patch('fedbiomed.researcher.responses.Responses.__init__')
    def test_private_load_training_replies(
            self,
            patch_responses_init,
            patch_responses_getitem
    ):
        """tests if `_load_training_replies` is loading file content from path file
        and is building a proper training replies structure from breakpoint info
        """

        # first test with a model done with pytorch
        pytorch_params = {
            # dont need other fields
            'model_params': torch.Tensor([1, 3, 5, 7])
        }
        sklearn_params = {
            # dont need other fields
            'model_params': np.array([[1, 2, 3, 4, 5], [2, 8, 7, 5, 5]])
        }
        # mock FederatedDataSet
        fds = MagicMock()
        fds.data = MagicMock(return_value={})

        # mock Pytorch model object
        model_torch = MagicMock(return_value=None)
        model_torch.save = MagicMock(return_value=None)
        func_torch_loadparams = MagicMock(return_value=pytorch_params)

        # mock Responses
        #
        # nota: works fine only with one instance of Response active at a time thus
        # - cannot be used in `test_save_private_training_replies`
        # - if testing on more than 1 round, only the last round can be used for Asserts
        def side_responses_init(data, *args):
            self.responses_data = data

        def side_responses_getitem(arg, *args):
            return self.responses_data[arg]

        patch_responses_init.side_effect = side_responses_init
        patch_responses_init.return_value = None
        patch_responses_getitem.side_effect = side_responses_getitem

        # instantiate job
        test_job_torch = Job(model=model_torch,
                             data=fds)
        # second create a `training_replies` variable
        loaded_training_replies_torch = [
            [
                {"success": True,
                 "msg": "",
                 "dataset_id": "dataset_1234",
                 "node_id": "node_1234",
                 "params_path": "/path/to/file/param.pt",
                 "timing": {"time": 0}
                 },
                {"success": True,
                 "msg": "",
                 "dataset_id": "dataset_4567",
                 "node_id": "node_4567",
                 "params_path": "/path/to/file/param2.pt",
                 "timing": {"time": 0}
                 }
            ]
        ]

        # action
        torch_training_replies = test_job_torch._load_training_replies(
            loaded_training_replies_torch,
            func_torch_loadparams
        )

        self.assertTrue(type(torch_training_replies) is dict)
        # heuristic check `training_replies` for existing field in input
        self.assertEqual(
            torch_training_replies[0][0]['node_id'],
            loaded_training_replies_torch[0][0]['node_id'])
        # check `training_replies` for pytorch models
        self.assertTrue(torch.isclose(torch_training_replies[0][1]['params'],
                                      pytorch_params['model_params']).all())
        self.assertTrue(torch_training_replies[0][1]['params_path'],
                        "/path/to/file/param2.pt")
        self.assertTrue(isinstance(torch_training_replies[0], Responses))

        ##### REPRODUCE TESTS BUT FOR SKLEARN MODELS AND 2 ROUNDS

        # create a `training_replies` variable
        loaded_training_replies_sklearn = [
            [
                {
                    # dummy
                    "params_path": "/path/to/file/param_sklearn.pt"
                }
            ],
            [
                {"success": False,
                 "msg": "",
                 "dataset_id": "dataset_8888",
                 "node_id": "node_8888",
                 "params_path": "/path/to/file/param2_sklearn.pt",
                 "timing": {"time": 6}
                 }
            ]
        ]

        # mock sklearn model object
        model_sklearn = MagicMock(return_value=None)
        model_sklearn.save = MagicMock(return_value=None)
        func_sklearn_loadparams = MagicMock(return_value=sklearn_params)
        # instantiate job
        test_job_sklearn = Job(model=model_sklearn,
                               data=fds)

        # action
        sklearn_training_replies = test_job_sklearn._load_training_replies(
            loaded_training_replies_sklearn,
            func_sklearn_loadparams
        )

        # heuristic check `training_replies` for existing field in input
        self.assertEqual(
            sklearn_training_replies[1][0]['node_id'],
            loaded_training_replies_sklearn[1][0]['node_id'])
        # check `training_replies` for sklearn models
        self.assertTrue(np.allclose(sklearn_training_replies[1][0]['params'],
                                    sklearn_params['model_params']))
        self.assertTrue(sklearn_training_replies[1][0]['params_path'],
                        "/path/to/file/param2_sklearn.pt")
        self.assertTrue(isinstance(sklearn_training_replies[0],
                                   Responses))

    @patch('fedbiomed.researcher.job.Job._load_training_replies')
    @patch('fedbiomed.researcher.job.Job.update_parameters')
    def test_load_state(
            self,
            patch_job_update_parameters,
            patch_job_load_training_replies
    ):
        """
        test if the job state values correctly initialize job
        """

        job_state = {
            'researcher_id': 'my_researcher_id_123456789',
            'job_id': 'my_job_id_abcdefghij',
            'model_params_path': '/path/to/my/model_file.py',
            'training_replies': {0: 'un', 1: 'deux'}
        }
        new_training_replies = {2: 'trois', 3: 'quatre'}

        # patch `update_parameters`
        patch_job_update_parameters.return_value = "dummy_string"

        # patch `_load_training_replies`
        patch_job_load_training_replies.return_value = new_training_replies

        # mock FederatedDataSet
        fds = MagicMock()
        fds.data = MagicMock(return_value={})

        # mock Pytorch model object
        model_object = MagicMock(return_value=None)
        model_object.save = MagicMock(return_value=None)

        # instantiate job
        test_job_torch = Job(model=model_object,
                             data=fds)

        # action
        test_job_torch.load_state(job_state)

        self.assertEqual(test_job_torch._researcher_id, job_state['researcher_id'])
        self.assertEqual(test_job_torch._id, job_state['job_id'])
        self.assertEqual(test_job_torch._training_replies, new_training_replies)

    @patch('fedbiomed.researcher.job.create_unique_link')
    @patch('fedbiomed.researcher.job.create_unique_file_link')
    @patch('fedbiomed.researcher.job.Job._save_training_replies')
    def test_save_state(
            self,
            patch_job_save_training_replies,
            patch_create_unique_file_link,
            patch_create_unique_link
    ):
        """
        test that job breakpoint state structure + file links are created
        """

        new_training_replies = [
            [
                {'params_path': '/path/to/job_test_save_state_params0.pt'}
            ],
            [
                {'params_path': '/path/to/job_test_save_state_params1.pt'}
            ]
        ]
        # expected transformed values of new_training_replies for save state
        new_training_replies_state = [
            [
                {'params_path': 'xxx/job_test_save_state_params0.pt'}
            ],
            [
                {'params_path': 'xxx/job_test_save_state_params1.pt'}
            ]
        ]

        link_path = '/path/to/job_test_save_state_params_link.pt'

        # patches configuration
        patch_create_unique_link.return_value = link_path

        def side_create_ufl(breakpoint_folder_path, file_path):
            return os.path.join(breakpoint_folder_path, os.path.basename(file_path))

        patch_create_unique_file_link.side_effect = side_create_ufl

        patch_job_save_training_replies.return_value = new_training_replies

        # mock FederatedDataSet
        fds = MagicMock()
        fds.data = MagicMock(return_value={})

        # mock Pytorch model object
        model_object = MagicMock(return_value=None)
        model_object.save = MagicMock(return_value=None)

        # instantiate job
        test_job_torch = Job(model=model_object,
                             data=fds)

        # choose arguments for saving state
        breakpoint_path = 'xxx'

        # action
        save_state = test_job_torch.save_state(breakpoint_path)

        self.assertEqual(environ['RESEARCHER_ID'], save_state['researcher_id'])
        self.assertEqual(test_job_torch._id, save_state['job_id'])
        self.assertEqual(link_path, save_state['model_params_path'])
        # check transformation of training replies
        for round_i, round in enumerate(new_training_replies):
            for response_i, _ in enumerate(round):
                self.assertEqual(
                    save_state['training_replies'][round_i][response_i]['params_path'],
                    new_training_replies_state[round_i][response_i]['params_path'])


if __name__ == '__main__':  # pragma: no cover
    unittest.main()
