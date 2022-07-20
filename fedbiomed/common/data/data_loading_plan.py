import uuid
from typing import List, Optional


class DataPipeline:
    """The building blocks of a DataLoadingPlan.

    A DataPipeline describes an intermediary layer between the researcher
    and the node's filesystem. It allows the node to specify a customization
    in the way data is "perceived" by the data loaders during training.

    A DataPipeline is identified by its type_id attribute. Thus this
    attribute should be unique among all DataPipelines in the same
    DataLoadingPlan. Moreover, we may test equality between a
    DataPipeline and a string by checking its type_id, as a means of
    easily testing whether a DataPipeline is contained in a collection.

    Correct usage of this class requires creating ad-hoc subclasses.
    The DataPipeline class is not intended to be instantiated directly.

    Subclasses of DataPipline must respect the following conditions:
    1. implement __init__ and call super's init
    2. overwrite self.type_id with a string that identifies the
       type of functionality expressed by the subclass
    3. extend the serialize(self) and a load(self, load_from: dict) function
    4. both serialize and load must call super's serialize and load respectively
    5. the load function must always return self
    6. the serialize function must update the dict returned by super's serialize
    """
    def __init__(self):
        super(DataPipeline, self).__init__()
        self.type_id = "abstract data pipeline"

    def __eq__(self, other):
        if isinstance(other, str):
            return self.type_id == other
        elif isinstance(other, DataPipeline):
            return self.type_id == other.type_id
        return False

    def serialize(self):
        """Serializes the class in a format similar to json.

        :return: a dictionary of key-value pairs sufficient for reconstructing
                 the DataPipeline.
        """
        return dict(
            pipeline_class=self.__class__.__name__,
            type_id=self.type_id
        )

    def load(self, load_from: dict):
        """Reconstruct the DataPipeline from a serialized version.

        :param load_from: a dictionary as obtained by the serialize function.
        :return: the self instance
        """
        self.type_id = load_from['type_id']
        return self


class MapperDP(DataPipeline):
    """A DataPipeline for mapping values.

    This Datapipeline can be used whenever an "indirect mapping" is needed.
    For example, it can be used to implement a correspondence between a set
    of "logical" abstract names and a set of folder names on the filesystem.

    Multiple instances of this pipeline may be used in the same DataLoadingPlan,
    provided that they are given different type_id via the constructor.
    """
    def __init__(self, type_id_: Optional[str] = None):
        super(MapperDP, self).__init__()
        if type_id_ is not None:
            self.type_id = type_id_
        self.map = {}

    def serialize(self):
        """Serializes the class in a format similar to json.

        Returns:
             a dictionary of key-value pairs sufficient for reconstructing
             the DataPipeline.
        """
        ret = super(MapperDP, self).serialize()
        ret.update({'map': self.map})
        return ret

    def load(self, load_from: dict):
        """Reconstruct the DataPipeline from a serialized version.

        Args:
            load_from: a dictionary as obtained by the serialize function.
        Returns:
            the self instance
        """
        super(MapperDP, self).load(load_from)
        self.map = load_from['map']
        return self


class DataLoadingPlan(List[DataPipeline]):
    """Customizations to the way the data is loaded and presented for training.

    A DataLoadingPlan is a list of DataPipelines. Each DataPipeline represents a
    customization, defined by the node, to the Dataset class (which is itself
    defined by the researcher).

    To exploit this functionality, a Dataset must be modified to accept the
    customizations provided by the DataLoadingPlan. To simplify this process,
    we provide the DataLoadingPlanMixin class below.

    The DataLoadingPlan class should be instantiated directly, no subclassing
    is needed. The DataLoadingPlan *is* a list, and exposes the same interface
    as a list.

    Additionally, the DataLoadingPlan overwrites the __getitem__ method to
    enable subscription by strings, where the string must match the type_id
    of the sought DataPipeline.

    Attrs:
        dlp_id: str representing a unique plan id (auto-generated)
        name: str representing an optional user-friendly name
    """
    def __init__(self, *args, **kwargs):
        super(DataLoadingPlan, self).__init__(*args, **kwargs)
        self.dlp_id = 'dlp_' + str(uuid.uuid4())
        self.name = ""

    def __getitem__(self, item):
        """Extend list's __getitem__ to string subscripts.

        Allows to quickly get a DataPipeline in a DataLoadingPlan by
        the operation [item: str], where item must match the type_id of the
        sought DataPipeline.

        If item is not a str, simply forwards the call to the __getitem__ of
        list.

        Args:
            item: a str matching the type_id of a DataPipeline, or anything that
            can be passed to a list's __getitem__
        Returns:
            the sought-after element
        Raises:
            ValueError if item is a str but does not match any DataPipelines
        """
        if isinstance(item, str):
            try:
                ret = next(dp for dp in self.__iter__() if dp == item)
            except StopIteration:
                raise ValueError(f'{item} not in DataLoadingPlan')
            return ret
        else:
            return super().__getitem__(item)

    def serialize(self):
        """Serializes the class in a format similar to json.

        Iteratively calls the serialize function of all its items.

        Returns:
             a dictionary of key-value pairs sufficient for reconstructing
             the DataLoadingPlan.
        """
        ret = dict(
            dlp_id=self.dlp_id,
            dlp_name=self.name,
            pipelines=[]
        )
        for pipeline in self.__iter__():
            ret['pipelines'].append(pipeline.serialize())
        return ret

    def load(self, load_from: dict):
        """Reconstruct the DataLoadingPlan from a serialized version.

        :warning: Calling this function will *clear* the contained
            DataPipelines. This function may not be used to "update"
            nor to "append to" a DataLoadingPlan.

        Args:
            load_from: a dictionary as obtained by the serialize function.
        Returns:
            the self instance
        """
        self.clear()
        self.dlp_id = load_from['dlp_id']
        self.name = load_from['dlp_name']
        for pipeline in load_from['pipelines']:
            self.append(DataPipeline().load(pipeline))
        return self

    def __str__(self):
        """User-friendly string representation"""
        return f"Data Loading Plan {self.name} id: {self.dlp_id} "\
               f"containing: {'; '.join([p.type_id for p in self.__iter__()])}"


class DataLoadingPlanMixin:
    """Utility class to enable DLP functionality in a dataset.

    Any Dataset class that inherits from DataLoadingPlanMixin will have the
    basic tools necessary to support a DataLoadingPlan. However, it will not
    have the logic to apply any specific DataLoadingPlan's DataPipeline.
    Therefore, the intended use of this class is to subclass it and create
    a MyDatasetDataLoadingPlanMixin that implements the logic specific to
    each DataPipeline. Typically, this logic will be implemented in the form
    of hooks that are called within the Dataset's implementation.
    """
    def __init__(self):
        self._dlp = None

    def set_dlp(self, dlp):
        self._dlp = dlp


