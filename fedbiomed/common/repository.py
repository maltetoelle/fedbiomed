import os

import requests  # Python built-in library
from typing import Callable, Dict, Any, Tuple, Text, Union
from fedbiomed.common.logger import logger

from fedbiomed.common.exceptions import FedbiomedRepositoryError
from fedbiomed.common.constants import ErrorNumbers
from json import JSONDecodeError


class Repository:
    """HTTP file repository from which to upload and download files.
    Files are uploaded from/dowloaded to a temporary file (`temp_fir`)
    Data uploaded should be:
    - python code (*.py file) that describes model +
    data handling/preprocessing
    - model params (under *.pt format)
    """
    def __init__(self,
                 uploads_url: Union[Text, bytes],
                 tmp_dir: str,
                 cache_dir: str):

        self.uploads_url = uploads_url
        self.tmp_dir = tmp_dir
        self.cache_dir = cache_dir  # unused

    def upload_file(self, filename: str) -> Dict[str, Any]:
        """
        uploads a file to a HTTP file repository (through an
        HTTP POST request).
        Args:
            filename (str): name/path of the file to upload.
        Returns:
            res (Dict[str, Any]): the result of the request under JSON
            format.
        Raises: 
            FedbiomedRepositoryError: when unable to read the file 'filename'
            FedbiomedRepositoryError: when POST HTTP request fails or returns
            a HTTP status 4xx (bad request) or 500 (internal server error)
            FedbiomedRepositoryError: when unable to deserialize JSON from
            the request
        """
        # first, we are trying to open the file `filename` and catch
        # any known exceptions related top `open` builtin function
        try:
            files = {'file': open(filename, 'rb')}
        except FileNotFoundError:
            _msg = ErrorNumbers.FB604.value + f': File {filename} not found, cannot upload it'
            logger.error(_msg)
            raise FedbiomedRepositoryError(_msg)
        except PermissionError:
            _msg = ErrorNumbers.FB604.value + f': Unable to read {filename} due to unsatisfactory privileges'
            ", cannot upload it"
            logger.error(_msg)
            raise FedbiomedRepositoryError(_msg)
        except OSError:
            _msg = ErrorNumbers.FB604.value + f': Cannot read file {filename} when uploading'
            logger.error(_msg)
            raise FedbiomedRepositoryError(_msg)

        # second, we are issuing an HTTP 'POST' request to the HTTP server

        _res = self._connection_handler(requests.post, self.uploads_url,
                                        filename, 'POST', files=files)
        # checking status of HTTP request

        self._raise_for_status_handler(_res, filename)

        # finally, we are deserializing message from JSON
        try:
            json_res = _res.json()
        except JSONDecodeError:
            # might be triggered by `request` package when deserializing
            _msg = 'Unable to deserialize JSON from HTTP POST request (when uploading file)'
            logger.error(_msg)
            raise FedbiomedRepositoryError(_msg)
        return json_res

    def download_file(self, url: str, filename: str) -> Tuple[int, str]:
        """
        downloads a file from a HTTP file repository (
            through an HTTP GET request)

        Args:
            url (str): url from which to download file
            filename (str): name of the temporary file

        Returns:
            status (int): HTTP status code
            filepath (str): the complete pathfile under
            which the temporary file is saved
        """

        res = self._connection_handler(requests.get, url, filename, 'GET')
        self._raise_for_status_handler(res, filename)
        filepath = os.path.join(self.tmp_dir, filename)

        try:
            open(filepath, 'wb').write(res.content)
        except FileNotFoundError as err:
            _msg = ErrorNumbers.FB604.value + str(err) + ', cannot save the downloaded content into it'
            logger.error(_msg)
            raise FedbiomedRepositoryError(_msg)
        except PermissionError:
            _msg = ErrorNumbers.FB604.value + f': Unable to read {filepath} due to unsatisfactory privileges'
            ", cannot write the downloaded content into it"
            logger.error(_msg)
            raise FedbiomedRepositoryError(_msg)
        except MemoryError:
            _msg = ErrorNumbers.FB604.value + f" : cannot write on {filepath}: out of memory!"
            logger.error(_msg)
            raise FedbiomedRepositoryError(_msg)
        except OSError:
            _msg = ErrorNumbers.FB604.value + f': Cannot open file {filepath} after downloading'
            logger.error(_msg)
            raise FedbiomedRepositoryError(_msg)

        return res.status_code, filepath

    def _raise_for_status_handler(self, rq_result: requests, filename: str = ''):
        """
        Handler that deals with exceptions and raises the appropriate 
        exception if the HTTP request has failed with a code error (eg 4xx or 500)

        Args:
            rq_result (requests): the HTTP request (eg `requests.post` result).
            filename (str, optional): the name of the file that is uploaded/downloaded, 
            (regarding the HTTP request issued).
            Defaults to ''.

        Raises:
            FedbiomedRepositoryError: if request has failed, raises an FedBiomedError
            with the appropriate code error/ message
        """
        _method_msg = self._get_method_request_msg(rq_result.request.method)
        try:
            # `raise_for_status` method raises an HTTPError if the status code 
            # is 4xx or 500
            rq_result.raise_for_status()
        except requests.HTTPError as err:
            if rq_result.status_code == 404:
                # handling case where status code of HTTP request equals 404
                _msg = ErrorNumbers.FB202.value + f' when {_method_msg} {filename}'

            else:
                # handling case where status code of HTTP request is 4xx or 500
                _msg = ErrorNumbers.FB203.value + f' when {_method_msg} {filename}' +\
                    f'(status code: {rq_result.status_code})'
            logger.error(_msg)
            logger.debug('Details of exception: ' + str(err))
            raise FedbiomedRepositoryError(_msg)
        else:
            logger.debug(f'upload (HTTP {rq_result.request.method} request) of file {filename} successful,' 
                         f' with status code {rq_result.status_code}')

    def _get_method_request_msg(self, req_type: str) -> str:
        """
        Returns the appropraite message whether the HTTP request is GET (downloading)
        or POST (uploading)

        Args:
            req_type (str): the request type ('GET', 'POST')

        Returns:
            str: the appropriate message (that will be used for the error message
            description if any error has been found)
        """
        if req_type.upper() == "POST":
            method_msg = "uploading file"
        elif req_type.upper() == "GET":
            method_msg = "downloading file"
        else:
            method_msg = 'issuing unknown HTTP request'
        return method_msg

    def _connection_handler(self,
                            callable_method: Callable,
                            url: str,
                            filename: str,
                            req_method: str,
                            *args,
                            **kwargs) -> requests:
        """
        Handles error that can trigger if the HTTP request fails (eg
        if request exceeded timeout, ...)

        Args:
            callable_method (Callable): the requests HTTP method (callable)
            url (str): the url method to which to connect to
            filename (str): the name of the file to upload / download
            req_method (str): the name of the HTTP request (eg 'POST', 'GET', ...)
            *args, **kwargs: argument to be passed to the callable method.

        Raises:
            FedbiomedRepositoryError: Triggers if the Timeout has exceeded.
            FedbiomedRepositoryError: Triggers if the request has faced too many redirect.
            FedbiomedRepositoryError: Triggers if URL is badly written, or missing some
            parts (eg: missing scheme).
            FedbiomedRepositoryError: Triggers if the connection was unsuccessful, when the service 
            to connect is unknown.         
            FedbiomedRepositoryError: Catches other exceptions coming from requests package

        Returns:
            requests: the result of the request if request is successful
        """
        _method_msg = self._get_method_request_msg(req_method)
        try:
            # issuing the HTTP request
            res = callable_method(url, *args, **kwargs)
        except requests.Timeout:
            # request exceeded timeout set 
            _msg = ErrorNumbers.FB201.value + f' : {req_method} HTTP request time exceeds Timeout'
            logger.error(_msg)
            raise FedbiomedRepositoryError(_msg)
        except requests.TooManyRedirects:
            # request had too any redirections
            _msg = ErrorNumbers.FB201.value + f' : {req_method} HTTP request exceeds max number of redirection'
            logger.error(_msg)
            raise FedbiomedRepositoryError(_msg)
        except (requests.URLRequired, ValueError) as err:
            # request has been badly formatted
            _msg = ErrorNumbers.FB604.value + f" : bad URL when {_method_msg} {filename}" + \
                "(details :" + str(err) + " )"
            logger.error(_msg)
            raise FedbiomedRepositoryError(_msg)
        except requests.ConnectionError:
            # an error during connection has occured
            _msg = ErrorNumbers.FB201.value + f' when {_method_msg} {filename}' + \
                f' to {self.uploads_url}: name or service not known'
            logger.error(_msg)
            raise FedbiomedRepositoryError(_msg)

        except requests.RequestException as err:
            # requests.ConnectionError should catch all exceptions
            # triggered by `requests` package
            _msg = ErrorNumbers.FB200.value + f': when {_method_msg} {filename}' + \
                f' (HTTP {req_method} request failed). Details: ' + str(err)
            logger.error(_msg)
            raise FedbiomedRepositoryError(_msg)
        return res
