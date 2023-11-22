"""
Authorlist state.

Read from json file.
"""
from __future__ import print_function

import json
from collections import defaultdict
import itertools
from datetime import datetime
import logging

from . import collabs as COLLABORATIONS
from .util import validate_author, author_ordering

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
            assert collab in COLLABORATIONS
        self._collab = collab
        self._authors = data['authors']
        self._institutions = data['institutions']
        self._thanks = data['thanks']
        self._acknowledgements = data['acknowledgements']

    def save(self, json_filename):
        data = {
            'acknowledgements': self._acknowledgements,
            'authors': sorted(self._authors, key=author_ordering),
            'institutions': self._institutions,
            'thanks': self._thanks,
        }

        with open(json_filename, 'w') as f:
            json.dump(data, f, indent=2, sort_keys=True)

    def authors(self, date, legacy=False):
        """
        List all valid authors on a date.

        Args:
            date (str): a date in ISO 8601 string format
            legacy (bool): list legacy authors (default: False)

        Returns: list of dicts
        """
        ret = []
        for author in self._authors:
            if self._collab and 'collab' in author and author['collab'] != self._collab:
                continue
            if author['from'] <= date and (author['to'] >= date or not author['to']):
                if legacy or not author.get('legacy', False):
                    ret.append(author)
        return ret

    def remove_author(self, author_data):
        """
        Completely remove an author with matching author_data.

        Args:
            author_data (dict): removed author information
        """
        for author in self._authors:
            if author == author_data:
                self._authors.remove(author)
                return
        raise Exception('could not find author')

    def add_author(self, author_data, collabs=None):
        """
        Add a new author.  Only check is that author is not active for the
        new dates, in the collab for the new author.

        Args:
            author_data (dict): new author information
        """
        logging.debug(f'{author_data}')

        username = author_data['keycloak_username']
        collab = author_data['collab']
        date_from = author_data['from']

        new_authors = [author_data]
        for author in self._authors:
            if username == author.get('keycloak_username', '') and collab == author.get('collab', ''):
                # found an author in the right collab
                # check date range
                if (not author['to']) or author['to'] >= date_from:
                    logging.info(f'author: {author}')
                    logging.info(f'author_data: {author_data}')
                    raise Exception('date range overlap')
            new_authors.append(author)

        self._authors = sorted(new_authors, key=author_ordering)

    def update_authors(self, author_data, collabs=None):
        """
        Set author data to a new value.

        Only updates matches based on:
        * keycloak_username
        * collab
        * from
        * instnames

        Args:
            author_data (list): new author information
            collabs (list): (optional) collaborations to update
        """
        logging.debug(f'{author_data}')
        if collabs:
            if any(c not in COLLABORATIONS for c in collabs):
                raise RuntimeError('invalid collaboration')
        elif (not collabs) and self._collab:
            collabs = [self._collab]

        # make sure data is valid
        for a in author_data:
            validate_author(a)

        username_set = {a['keycloak_username'] for a in author_data}
        if len(username_set) > 1:
            raise RuntimeError('cannot update more than one author')
        username = list(username_set)[0]
        if not username:
            raise RuntimeError('keycloak_username must be set')

        new_authors = []
        current_author_data = []
        for author in self._authors:
            if username == author.get('keycloak_username', ''):
                if (not collabs) or author.get('collab', '') in collabs:
                    current_author_data.append(author)
                    continue
            new_authors.append(author)

        if not current_author_data:
            logging.info(f'adding new authors: {[a["keycloak_username"] for a in author_data]}')
            new_authors.extend(author_data)
        elif {a['collab'] for a in current_author_data} == {a['collab'] for a in author_data}:
            # matching collab update
            for a in author_data:
                for ca in current_author_data:
                    if all(a[k] == ca[k] for k in ('collab', 'from', 'instnames')):
                        # match
                        logging.info(f'editing author: {a["keycloak_username"]}')
                        new_authors.append(a)
                        current_author_data.remove(ca)
                        break
                else:
                    logging.info(f'author: {a}')
                    logging.info(f'current_author_data: {current_author_data}')
                    raise Exception('did not find match')
            # add all authors not matched (generally older data)
            new_authors.extend(current_author_data)
        else:
            logging.info(f'author_data: {author_data}')
            logging.info(f'current_author_data: {current_author_data}')
            raise Exception('unknown update type')

        self._authors = sorted(new_authors, key=author_ordering)

    def institutions(self, date, **kwargs):
        """
        List all valid institutions on a date.

        Args:
            date (str): a date in ISO 8601 string format

        Returns: dict of dicts
        """
        insts = {}
        for a in itertools.chain(self.authors(date, **kwargs)):
            if 'instnames' in a and a['instnames']:
                for inst in a['instnames']:
                    inst_data = self._institutions[inst]
                    if self._collab and 'collabs' in inst_data and self._collab not in inst_data['collabs']:
                        continue
                    insts[inst] = inst_data
        return insts

    def thanks(self, date, **kwargs):
        """
        List all valid thanks on a date.

        Args:
            date (str): a date in ISO 8601 string format

        Returns: dict
        """
        thanks = {}
        for a in itertools.chain(self.authors(date, **kwargs)):
            if 'thanks' in a and a['thanks']:
                for t in a['thanks']:
                    thanks[t] = self._thanks[t]
        return thanks
        ## TODO: actually support dates for thanks

    def acknowledgements(self, date):
        """
        List all valid acknowledgements on a date.

        Args:
            date (str): a date in ISO 8601 string format

        Returns: list of strings
        """
        ret = []
        for ack in self._acknowledgements:
            if ack['from'] <= date and (ack['to'] >= date or not ack['to']):
                ret.append(ack['value'])
        if ret and ret[-1][-1] == ';':
            ret[-1] = ret[-1][:-1]+'.'
        return ret
