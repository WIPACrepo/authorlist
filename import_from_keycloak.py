import asyncio
from datetime import datetime, timedelta
import logging
from collections import defaultdict
from pprint import pprint

from krs.token import get_rest_client
from krs.users import user_info
from krs.groups import get_group_membership
from krs.institutions import list_insts

from authorlist.state import State
from authorlist.keycloak_utils import IceCube, IceCubeGen2

import unidecode


user_cache = {}
async def get_keycloak_users(group, rest_client=None):
    def clean(user):
        firstName = user['attributes'].get('author_firstName', '')
        if not firstName:
            firstName = user['firstName']
        lastName = user['attributes'].get('author_lastName', '')
        if not lastName:
            lastName = user['lastName']
        email = user['attributes'].get('author_email', '')
        if not email:
            email = user.get('email', '')
        return {
            'attributes': user['attributes'],
            'firstName': firstName,
            'lastName': lastName,
            'username': user['username'],
            'email': email,
        }
    users = await get_group_membership(group, rest_client=rest_client)
    ret = []
    for u in users:
        if u not in user_cache:
            user_cache[u] = await user_info(u, rest_client=rest_client)
        try:
            ret.append(clean(user_cache[u]))
        except:
            pprint(user_cache[u])
            raise
    return ret

def make_username(author):
    ret = unidecode.unidecode(author['first'].lower())[0]+unidecode.unidecode(author['last'].lower())
    ret = ret.replace('"', '').replace("'", '').replace(' ', '')
    return ret[:15]

def match_one(author, user):
    if 'keycloak_username' in author:
        return author['keycloak_username'] == user['username']
    if author['email'] == user.get('email', -1):
        return True
    if author['email'].split('@')[0] == user['username']:
        return True
    afirst = unidecode.unidecode(author['first'].lower())
    alast = unidecode.unidecode(author['last'].lower())
    ufirst = unidecode.unidecode(user.get('firstName','').lower())
    ulast = unidecode.unidecode(user.get('lastName','').lower())
    if len(afirst) > 1 and afirst[1] == '.':
        afirst = afirst[0]
        ufirst = ufirst[0]
    if afirst == ufirst and alast == ulast:
        return True
    # this is dangerous, and could match similar people, since it only uses the first letter of the first name
    #username = make_username(author)
    #if user['username'].startswith(username):
    #    return True
    return False

def match_users(authorlist, keycloak):
    matches = []
    for au in authorlist:
        for ku in keycloak:
            if match_one(au, ku):
                matches.append((au,ku))
                break
    return matches


async def sync(state, filename_out, experiment, dryrun=False, client=None):
    if experiment.lower() == 'icecube':
        authorlist_insts_to_groups = IceCube.authorlist_insts_to_groups
        groups_to_authorlist_insts = IceCube.groups_to_authorlist_insts
    elif experiment.lower() == 'icecube-gen2':
        authorlist_insts_to_groups = IceCubeGen2.authorlist_insts_to_groups
        groups_to_authorlist_insts = IceCubeGen2.groups_to_authorlist_insts
    else:
        raise Exception(f'invalid experiment: {experiment}')

    # check our institution mappings
    now = datetime.utcnow().isoformat()
    now_date = datetime.utcnow().date()
    logging.info('now timestamp %s', now)
    authors = state.authors(now)
    author_insts = state.institutions(now)
    for i in author_insts:
        if i not in authorlist_insts_to_groups:
            raise Exception(f'inst {i} is not in authorlist->keycloak mapping')

    krs_insts_raw = await list_insts(experiment, rest_client=client)
    krs_insts = {}
    for k in krs_insts_raw:
        if krs_insts_raw[k].get('authorlist', 'false') == 'true':
            base_name = k.split('/')[-1].lower()
            if 'authorlists' in krs_insts_raw[k]:
                for name in krs_insts_raw[k]['authorlists']:
                    krs_insts[base_name+'-'+name] = k+'/authorlist-'+name
            else:
                krs_insts[base_name] = k+'/authorlist'
    for i in krs_insts.values():
        if i not in groups_to_authorlist_insts:
            raise Exception(f'group {i} is not in keycloak->authorlist mapping')

    authors_by_username = {}
    for a in authors:
        if 'keycloak_username' not in a:
            logging.error('missing keycloak username for author: %r', a)
            raise Exception('missing keycloak username for author')
        if a['keycloak_username'] in authors_by_username:
            logging.error(f'author {a} is duplicated. orig: {authors_by_username[a["keycloak_username"]]}')
            raise Exception('dup author in authorlist')
        authors_by_username[a['keycloak_username']] = a

    # now check users
    new_author_insts = defaultdict(set)
    updated_author_data = defaultdict(dict)
    for authorlist_inst, keycloak_group in authorlist_insts_to_groups.items():
        logging.warning(f'processing {authorlist_inst} {keycloak_group}')
        authorlist_users = [a for a in authors if authorlist_inst in a['instnames']]

        keycloak_users = await get_keycloak_users(keycloak_group, rest_client=client)

        matches = match_users(authorlist_users, keycloak_users)

        for author in authorlist_users:
            for au,ku in matches:
                if author == au:
                    break
            else:
                #remove_authors[author['keycloak_username']].append(authorlist_inst)
                logging.warning(f'   authorlist extra user: {author["first"]} {author["last"]} {author["email"]}')
        for user in keycloak_users:
            for au,ku in matches:
                if user == ku: # found match
                    # check for attr updates
                    attr_update = False
                    a = au.copy()
                    if ku['email'] and au['email'] != ku['email']:
                        logging.warning(f'   keycloak email update: {user["username"]}  {au["email"]} -> {ku["email"]}')
                        a['email'] = ku['email']
                        attr_update = True
                    if ku['firstName'] and au['first'] != ku['firstName']:
                        logging.warning(f'   keycloak firstName update: {user["username"]}  {au["first"]} -> {ku["firstName"]}')
                        a['first'] = ku['firstName']
                        attr_update = True
                    if ku['lastName'] and au['last'] != ku['lastName']:
                        logging.warning(f'   keycloak lastName update: {user["username"]}  {au["last"]} -> {ku["lastName"]}')
                        a['last'] = ku['lastName']
                        attr_update = True
                    authname = ku['attributes'].get('author_name', '').strip()
                    if authname and au['authname'] != authname:
                        logging.warning(f'   keycloak authname update: {user["username"]}  {au["authname"]} -> {authname}')
                        a['authname'] = authname
                        attr_update = True
                    orcid = ku['attributes'].get('orcid', '').strip()
                    if orcid and au['orcid'] != orcid:
                        logging.warning(f'   keycloak orcid update: {user["username"]}  {au["orcid"]} -> {orcid}')
                        a['orcid'] = orcid
                        attr_update = True
                    thanks = user['attributes'].get(f'authorlist_{experiment.lower()}_thanks', [])
                    if isinstance(thanks, str):
                        thanks = [thanks]
                    if au['thanks'] != thanks:
                        logging.warning(f'   keycloak thanks update: {user["username"]}  {au["thanks"]} -> {thanks}')
                        a['thanks'] = thanks
                        attr_update = True

                    if attr_update:
                        updated_author_data[user['username']] = a

                    new_author_insts[user['username']].add(authorlist_inst)
                    break
            else:
                logging.warning(f'   keycloak extra user: {user["username"]}')
                new_author_insts[user['username']].add(authorlist_inst)
                if user['username'] not in updated_author_data:
                    authname = user['attributes'].get('author_name', '').strip()
                    if not authname:
                        authname = (user['firstName'][0]+'. '+user['lastName']).title()
                    thanks = user['attributes'].get(f'authorlist_{experiment.lower()}_thanks', [])
                    if isinstance(thanks, str):
                        thanks = [thanks]
                    updated_author_data[user['username']] = {
                        'authname': authname,
                        'collab': experiment.lower(),
                        'email': user['email'],
                        'first': user['firstName'],
                        'from': now_date.isoformat(),
                        'instnames': [],
                        'keycloak_username': user['username'],
                        'last': user['lastName'],
                        'orcid': user['attributes'].get('orcid', '').strip(),
                        'thanks': thanks,
                        'to': '',
                    }

    # remove/update existing authors
    for username in sorted(authors_by_username):
        a = authors_by_username[username]
        if username not in new_author_insts:
            logging.info(f'removing {username}')
            remove_author = a.copy()
            remove_author['to'] = (now_date-timedelta(days=1)).isoformat()
            if remove_author['to'] < remove_author['from']:
                logging.info(f'    completely overwrite prev update to {username}')
                state.remove_author(a)
            else:
                state.update_authors([remove_author])
        elif new_author_insts[username] == set(a['instnames']) and username not in updated_author_data:
            continue  # no updates
        else:
            logging.info(f'updating {username}')
            update_author = updated_author_data[username] if username in updated_author_data else a.copy()
            update_author['instnames'] = sorted(new_author_insts[username])
            update_author['from'] = now_date.isoformat()
            remove_author = a.copy()
            remove_author['to'] = (now_date-timedelta(days=1)).isoformat()
            if remove_author['to'] < remove_author['from']:
                logging.info(f'    completely overwrite prev update to {username}')
                state.remove_author(a)
            else:
                state.update_authors([remove_author])
            state.add_author(update_author)

    # add new authors
    for username in sorted(new_author_insts):
        if username not in authors_by_username:
            a = updated_author_data[username]
            a['instnames'] = sorted(new_author_insts[username])
            logging.info(f'adding author {a["keycloak_username"]} with insts {a["instnames"]}')
            state.add_author(a)

    state.save(filename_out)

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Export to Keycloak')
    parser.add_argument('filename', help='author list json filename')
    parser.add_argument('filename_out', help='author list json filename')
    parser.add_argument('--experiment', default='IceCube', help='experiment to filter by')
    parser.add_argument('--log-level', default='info', choices=('debug', 'info', 'warning', 'error'), help='logging level')
    parser.add_argument('--dryrun', action='store_true', help='dry run')
    args = vars(parser.parse_args())

    logging.basicConfig(level=getattr(logging, args['log_level'].upper()))

    keycloak_client = get_rest_client()

    state = State(args['filename'], collab=args['experiment'].lower())
    
    asyncio.run(sync(state, args['filename_out'], experiment=args['experiment'], dryrun=args['dryrun'], client=keycloak_client))

if __name__ == '__main__':
    main()
