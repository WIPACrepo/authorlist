import asyncio
from datetime import datetime
import logging
from pprint import pprint, pformat

from krs.token import get_rest_client
from krs.users import list_users, user_info
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

def match_users(authorlist, keycloak):
    matches = []
    for au in authorlist:
        for ku in keycloak:
            if ((au['last'].lower() == ku['lastName'].lower() and au['first'][0].lower() == ku['firstName'][0].lower())
                or (au['email'] == ku['email'])
                or (au['email'].split('@')[0] == ku['username'])):
                matches.append((au,ku))
                break
            username = unidecode.unidecode(au['first'][0].loewr()+au['last'].lower())
            if username == ku['username']:
                matches.append((au,ku))
                break
        else:
            logging.error('authorlist user: %r', au)
            logging.info('keycloak_users: %s', pformat(keycloak))
            raise Exception('Match Error')
    return matches

async def export(state, experiment, dryrun=False, client=None):
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
    for authorlist_inst, keycloak_group in authorlist_insts_to_groups.items():
        print('processing', authorlist_inst, keycloak_group)
        authorlist_users = [a for a in state.authors(now) if authorlist_inst in a['instnames']]

        # 1) is the user in the regular institution group?
        group = '/'.join(keycloak_group.split('/')[:-1])
        keycloak_users = await get_keycloak_users(group, rest_client=client)

        match_users(authorlist_users, keycloak_users)
        break



    

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Export to Keycloak')
    parser.add_argument('filename', help='author list json filename')
    parser.add_argument('--experiment', default='IceCube', help='experiment to filter by')
    parser.add_argument('--log-level', default='info', choices=('debug', 'info', 'warning', 'error'), help='logging level')
    parser.add_argument('--dryrun', action='store_true', help='dry run')
    args = vars(parser.parse_args())

    logging.basicConfig(level=getattr(logging, args['log_level'].upper()))

    keycloak_client = get_rest_client()

    state = State(args['filename'], collab=args['experiment'].lower())
    
    asyncio.run(export(state, experiment=args['experiment'], dryrun=args['dryrun'], client=keycloak_client))

if __name__ == '__main__':
    main()
