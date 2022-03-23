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
        return {
            'attributes': user['attributes'],
            'firstName': user['firstName'],
            'lastName': user['lastName'],
            'username': user['username'],
            'email': user.get('email',''),
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
    afirst = unidecode.unidecode(author['first'].lower())
    alast = unidecode.unidecode(author['last'].lower())
    ufirst = unidecode.unidecode(user.get('firstName','').lower())
    ulast = unidecode.unidecode(user.get('lastName','').lower())
    if len(afirst) > 1 and afirst[1] == '.':
        afirst = afirst[0]
        ufirst = ufirst[0]
    if afirst == ufirst and alast == ulast:
        return True
    if author['email'] == user.get('email', -1):
        return True
    if author['email'].split('@')[0] == user['username']:
        return True
    username = make_username(author)
    if user['username'].startswith(username):
        return True
    return False

def match_users(authorlist, keycloak):
    matches = []
    for au in authorlist:
        for ku in keycloak:
            if match_one(au, ku):
                matches.append((au,ku))
                break
    return matches

def check(data):
    for a in data['authors']:
        if 'instnames' in a:
            for inst in a['instnames']:
                if inst not in data['institutions']:
                    print(a['authname'],inst)
                    raise Exception('bad instname')
        if 'thanks' in a:
            for t in a['thanks']:
                if t not in data['thanks']:
                    print(a['authname'],t)
                    raise Exception('bad thanks')
        if 'instnames' not in a and 'thanks' not in a:
            print(a['authname'])
            raise Exception('no instname or thanks')

def save(outfile, data):
    check(data)
    data['authors'].sort(key=author_ordering)

    if outfile:
        with open(outfile, 'w') as f:
            json.dump(data, f, indent=2, sort_keys=True)
    else:
        pprint(data)


async def to_json(state, filename_out, experiment, dryrun=False, client=None):
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

    # now check users
    remove_authors = defaultdict(list)
    add_authors = {}
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
                remove_authors[author['keycloak_username']].append(authorlist_inst)
                logging.warning(f'   authorlist extra user: {author["first"]} {author["last"]} {author["email"]}')
        for user in keycloak_users:
            for au,ku in matches:
                if user == ku:
                    break
            else:
                t = user['attributes'].get(f'authorlist_{experiment.lower()}_thanks', [])
                if isinstance(t, str):
                    t = [t]
                if user['username'] in add_authors:
                    add_authors[user['username']]['instnames'].append(authorlist_inst)
                else:
                    authname = user['attributes'].get('author_name', '')
                    if not authname:
                        authname = (user['firstName'][0]+'. '+user['lastName']).title()
                    add_authors[user['username']] = {
                        'authname': authname,
                        'collab': experiment.lower(),
                        'email': user.get('email',''),
                        'first': user['firstName'],
                        'from': now_date.isoformat(),
                        'instnames': [authorlist_inst],
                        'keycloak_username': user['username'],
                        'last': user['lastName'],
                        'orcid': user['attributes'].get('orcid', ''),
                        'thanks': t,
                        'to': '',
                    }
                logging.warning(f'   keycloak extra user: {user["username"]}')

    # remove/update existing authors
    for a in remove_authors:
        for ca in authors:
            if ca['keycloak_username'] == a:
                remove_insts = set(remove_authors[a])
                prev_insts = set(ca['instnames'])
                remove_author = ca.copy()
                remove_author['to'] = (now_date-timedelta(days=1)).isoformat()
                if remove_author['to'] < remove_author['from']:
                    logging.info(f'completely remove {ca["keycloak_username"]}')
                    state.remove_author(ca)
                else:
                    state.update_authors([remove_author])

                if remove_insts != prev_insts:
                    # remove and update
                    if ca['username'] in add_authors:
                        add_authors[user['username']]['instnames'].extend(prev_insts-remove_insts)
                    else:
                        ca['instnames'] = list(prev_insts-remove_insts)
                        add_authors[user['username']] = ca

                break
        else:
            raise Exception(f'could not find author {a}')

    # add new authors
    for a in add_authors.values():
        # make sure insts are not dups
        a['instnames'] = sorted(set(a['instnames']))
        state.update_authors([a])

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
    
    asyncio.run(to_json(state, args['filename_out'], experiment=args['experiment'], dryrun=args['dryrun'], client=keycloak_client))

if __name__ == '__main__':
    main()
