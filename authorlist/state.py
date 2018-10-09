"""
Authorlist state.

Read from json file.
"""
from __future__ import print_function

import json
from collections import defaultdict
import itertools
from datetime import datetime

PINGU_START_DATE = '2013-06-25'
GEN2_START_DATE = '2014-12-16'

class State:
    """
    The authorlist state.

    Args:
        json_filename (str): name of json file holding state
        collab (str): (optional) name of collaboration to filter by
    """
    def __init__(self, json_filename, collab=None):
        with open(json_filename) as f:
            data = json.load(f)

        if collab:
            self._authors = []
            for author in data['authors']:
                if 'collab' in author and author['collab'] != collab:
                    continue
                self._authors.append(author)
            self._institutions = {}
            for name in data['institutions']:
                inst = data['institutions']
                if 'collabs' in inst and collab not in inst['collabs']:
                    continue
                self._institutions[name] = inst
            self._thanks = data['thanks']
            self._acknowledgements = data['acknowledgements']
        else:
            self._authors = data['authors']
            self._institutions = data['institutions']
            self._thanks = data['thanks']
            self._acknowledgements = data['acknowledgements']

    def authors(date):
        """
        List all valid authors on a date.

        Args:
            date (str): a date in ISO 8601 string format

        Returns: list of dicts
        """
        ret = []
        for author in self._authors:
            if author['from'] <= date and author['to'] >= date:
                ret.append(author)
        return ret

    def institutions(date):
        """
        List all valid institutions on a date.

        Args:
            date (str): a date in ISO 8601 string format

        Returns: dict of dicts
        """
        return self._institutions
        ## TODO: actually support dates for institutions
        ret = {}
        for name in self._institutions:
            inst = self._institutions[name]
            if inst['from'] <= date and inst['to'] >= date:
                ret[name] = inst
        return ret

    def thanks(date):
        """
        List all valid thanks on a date.

        Args:
            date (str): a date in ISO 8601 string format

        Returns: dict
        """
        return self._thanks
        ## TODO: actually support dates for thanks

    def acknowledgements(date):
        """
        List all valid acknowledgements on a date.

        Args:
            date (str): a date in ISO 8601 string format

        Returns: list of strings
        """
        ret = []
        for ack in self._acknowledgements:
            if ack['from'] <= date and ack['to'] >= date:
                ret.append(ack['value'])
        return ret
