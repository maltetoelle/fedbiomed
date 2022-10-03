"""
"""

from copy import deepcopy
from typing import Dict, Iterable, Iterator, List, Mapping, OrderedDict, Union

from fedbiomed.common.constants import TrainingPlans
from fedbiomed.common.exceptions import FedbiomedAggregatorError

from fedbiomed.common.training_plans import BaseTrainingPlan

from fedbiomed.researcher.aggregators.aggregator import Aggregator
from fedbiomed.researcher.aggregators.functional import federated_averaging
from fedbiomed.researcher.aggregators.functional import initialize

from fedbiomed.common.exceptions import FedbiomedAggregatorError
from fedbiomed.researcher.datasets import FederatedDataSet

import torch
import numpy as np


class Scaffold(Aggregator):
    """
    Defines the Scaffold strategy
    
    Attributes:
     - aggregator_name(str): name of the aggregator 
     - nodes_correction_states(Dict[str, Mapping[str, Union[torch.tensor, np.ndarray]]]): corrections
     parameters obtained for each client
    """

    def __init__(self, server_lr: float):
        """Constructs `Scaffold` object as an instance of [`Aggregator`]
        [fedbiomed.researcher.aggregators.Aggregator].
        
        Despite being an algorithm of choice for federated learning, it is observed that FedAvg
        suffers from `client-drift` when the data is heterogeneous (non-iid), resulting in unstable and slow
        convergence. SCAFFOLD uses control variates (variance reduction) to correct for the `client-drift` in its local
        updates.
        Intuitively, SCAFFOLD estimates the update direction for the server model (c) and the update direction for each
        client (c_i).
        The difference (c - c_i) is then an estimate of the client-drift which is used to correct the local update.
        
        References:
        [Scaffold: Stochastic Controlled Averaging for Federated Learning][https://arxiv.org/abs/1910.06378]
        
        Args:
            server_lr (float): server's (or Researcher's) learning rate
            
        """
        super(Scaffold, self).__init__()
        self.aggregator_name: str = "Scaffold"
        if server_lr == 0.:
            raise FedbiomedAggregatorError("SCAFFOLD Error: Server learning rate cannot be equal to 0")
        self.server_lr: float = server_lr
        self.nodes_correction_states: Dict[str, Mapping[str, Union[torch.tensor, np.ndarray]]] = None

        self.nodes_lr: Iterable[float] = None

    def aggregate(self, model_params: list,
                  weights: list,
                  global_model: Mapping[str, Union[torch.tensor, np.ndarray]],
                  training_plan: BaseTrainingPlan,
                  node_ids: Iterable[str],
                  n_updates: int = 1,
                  n_round: int = 0,
                  *args, **kwargs) -> Dict:
        """
        Aggregates local models coming from nodes into a global model, using SCAFFOLD algorithm (2nd option)
        
        Performed computations:
        -----------------------
        
        c_i(+) <- c_i - c + 1/(K*eta_l)(x - y_i)
        

        Args:
            model_params (list): _description_
            weights (list): _description_
            global_model (Mapping[str, Union[torch.tensor, np.ndarray]]): _description_
            training_plan (BaseTrainingPlan): _description_
            node_ids (Iterable[str]): _description_
            n_updates (int, optional): _description_. Defaults to 1.
            n_round (int, optional): _description_. Defaults to 0.

        Returns:
            Dict: _description_
        """

    
        weights_processed = [list(weight.values())[0] for weight in weights] # same retrieving
        
        model_params_processed = self.scaling(model_params, global_model)
        model_params_processed = [list(model_param.values())[0] for model_param in model_params] # model params are contained in a dictionary with node_id as key, we just retrieve the params

        #model_params_processed = list(model_params_processed.values())

        weights_processed = self.normalize_weights(weights_processed)
        aggregated_parameters = federated_averaging(model_params_processed, weights_processed)
        
        self.set_nodes_learning_rate_from_training_plan(training_plan)
        if n_round == 0:
            self.init_correction_states(global_model, node_ids)
        self.update_correction_states(aggregated_parameters, global_model,  node_ids, n_updates)
        return aggregated_parameters

    def get_aggregator_args(self, global_model: Mapping[str, Union[torch.tensor, np.ndarray]], node_ids: Iterator[str]) -> Dict:
        """Sends additional arguments for aggregator. For scaffold, it is mainly correction

        Args:
            global_model (Mapping[str, Union[torch.tensor, np.ndarray]]): _description_
            node_ids (Iterator[str]): _description_

        Returns:
            Dict: _description_
        """
        if self.nodes_correction_states is None:
            self.init_correction_states(global_model, node_ids) # making parameters JSON serializable
        aggregator_args = {}
        for node_id in node_ids:
            # serializing correction parameters
            
            serialized_aggregator_correction = {key: tensor.tolist() for key, tensor in self.nodes_correction_states[node_id].items()}
            aggregator_args.update({node_id: {'aggregator_name': self.aggregator_name,
                                              'aggregator_correction': serialized_aggregator_correction}})
        
        return aggregator_args

    def check_values(self, node_lrs: List[float], n_updates: int):
        """
        This method checks if all values are correct and have been set before using aggregator.
        Raises error otherwise
        This can prove usefull, so that user will have errors before performing first round of training

        Args:
            lr (float): _description_

        Raises:
            FedbiomedAggregatorError: _description_
        """
        # check if values are non zero
        if not node_lrs.any():
            raise FedbiomedAggregatorError(f"Learning rate(s) should be non-zero, but got {node_lrs} ")
        if n_updates == 0 or int(n_updates) != float(n_updates):
            raise FedbiomedAggregatorError(f"n_updates should be a non zero integer, but got n_updates: {n_updates} in SCAFFOLD aggregator")
        if self._fds is None:
            raise FedbiomedAggregatorError(" Federated Dataset not provided, but needed for Scaffold")

    def set_nodes_learning_rate_from_training_plan(self, training_plan: BaseTrainingPlan) -> Iterable[float]:
        # to be implemented in a utils module
        
        lrs: List[float] = training_plan.get_learning_rate()
        n_model_layers = len(training_plan.get_model_params())
        
        if len(lrs) == 1:
            # case where there is one learning rate
            lr = lrs * n_model_layers
            
        elif len(lrs) == n_model_layers:
            # case where there are several learning rates value
            lr = lrs
        else:
            _arg_name = ''
            if self._training_plan_type == TrainingPlans.SkLearnTrainingPlan:
                _arg_name = 'model_args'
            elif self._training_plan_type == TrainingPlans.TorchTrainingPlan:
                _arg_name = 'training_args'
            raise FedbiomedAggregatorError(f"Error when setting node learning rate for SCAFFOLD: cannot extract node learning rate. As a quick fix, please specify learning rate value in the {_arg_name}")
        self.nodes_lr = lr
        return self.nodes_lr

    def init_correction_states(self,
                               global_model: Mapping[str, Union[torch.tensor, np.ndarray]],
                               node_ids: Iterable[str],
                               ):
        # initialize nodes states

        init_params = {key:initialize(tensor)[1]for key, tensor in global_model.items()}
        self.nodes_correction_states = {node_id: deepcopy(init_params) for node_id in node_ids}
    
    def scaling(self,
                model_params: List[Dict[str, Mapping[str, Union[torch.Tensor, np.ndarray]]]],
                global_model: Mapping[str, Union[torch.tensor, np.ndarray]]) -> List[Dict[str, Mapping[str, Union[torch.Tensor, np.ndarray]]]]:
        """
        Computes `x (1 - eta_g) + eta_g * y_i`
        Proof: 
            x <- x + eta_g * grad(x)
            x <- x + eta_g / S * sum_i(y_i - x)
            x <- x (1 - eta_g) + eta_g / S * sum_i(y_i)
            x <- sum_i(x (1 - eta_g) + eta_g * y_i) / S
            x <- avg(x (1 - eta_g) + eta_g * y_i) ... averaging is done afterwards

        Args:
            model_params (list): _description_
            global_model (OrderedDict): _description_

        Returns:
            list: _description_
        """
        # refers as line 13 and 17 in pseudo code
        # should scale regading option
        for idx, model_param in enumerate(model_params):
            node_id = list(model_param.keys())[0] # retrieve node_id
            for layer in model_param[node_id]:
                model_params[idx][node_id][layer] = model_param[node_id][layer] * self.server_lr + (1 - self.server_lr) * global_model[layer]
        return model_params
        
    def update_correction_states(self, updated_model_params: Mapping[str, Union[torch.tensor, np.ndarray]],
                                 global_model: Mapping[str, Union[torch.tensor, np.ndarray]],
                                 node_ids: Iterable[str], n_updates: int=1,):
        """_summary_
        
        Proof:
        
        c <- c + S/N grad(c)
        c <- c + 1/N sum_i(c_i(+) - c_i)
        c <- c + 1/N * sum_i( 1/ (K * eta_l)(x - y_i) - c)

        Args:
            updated_model_params (dict): _description_
            global_model (OrderedDict): _description_
            lr (float): _description_
            node_ids (Iterator[str]): Iterable of all nodes taking part in the round
            n_updates (int, optional): _description_. Defaults to 1.
        """
        # refers as line 12, 13 and 17 in pseudo code
        if self._fds is None:
            raise FedbiomedAggregatorError("Cannot run SCAFFOLD aggregator: No Federated Dataset set")
        total_nb_nodes = len(self._fds.node_ids())  # get the total number of nodes
        
        weights = [1/total_nb_nodes] * len(node_ids)

        present_nodes_idx = list(range(len(self._fds.node_ids())))
        
        for idx, node_id in enumerate(self._fds.node_ids()):
            if node_id not in node_ids:
                present_nodes_idx.remove(idx)
        
        assert len(present_nodes_idx) == len(node_ids)
        # get weights for weighted summation
        _tmp_correction_update = []
        
        for idx, node_id in enumerate( node_ids):
            
            _tmp_correction_update.append({})
            #_tmp_correction_update[idx][node_id] = {}
            lrs = self.nodes_lr
            for idx_layer, (layer_name, node_layer) in enumerate(updated_model_params.items()): # iterate params of each client
                
                # `_tmp_correction_update`` is an intermediate variable equals to 1/ (K * eta_l)(x - y_i) - c

                _tmp_correction_update[idx][layer_name] = (global_model[layer_name] - node_layer) / (self.server_lr * lrs[idx_layer] * n_updates)
                # FIXME: check why we need node learning_rate(s) in above formulae
                _tmp_correction_update[idx][layer_name] = _tmp_correction_update[idx][layer_name] - self.nodes_correction_states[node_id][layer_name]

        

        _aggregated_tmp_correction_update = federated_averaging(_tmp_correction_update, weights)
        
        # finally, perform `c <- c + S/N \Delta{c}`
        for node_id in self._fds.node_ids():
            for layer_name, node_layer in updated_model_params.items(): 

                self.nodes_correction_states[node_id][layer_name] += _aggregated_tmp_correction_update[layer_name]

    def set_training_plan_type(self, training_plan_type: TrainingPlans) -> TrainingPlans:
        """
        Overrides `set_training_plan_type` from parent class. 
        Checks if trainning plan type, and if it is SKlearnTrainingPlan,
        raises an error.

        Args:
            training_plan_type (TrainingPlans): _description_

        Raises:
            FedbiomedAggregatorError: _description_

        Returns:
            TrainingPlans: _description_
        """
        training_plan_type = super().set_training_plan_type(training_plan_type)
        if training_plan_type == TrainingPlans.SkLearnTrainingPlan:
            raise FedbiomedAggregatorError("Aggregator SCAFFOLD not implemented for SKlearn")
        return training_plan_type
