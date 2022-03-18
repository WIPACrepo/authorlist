import asyncio
from datetime import datetime
import logging
from pprint import pprint, pformat

from krs.token import get_rest_client
from krs.users import list_users, user_info, modify_user
from krs.groups import get_group_membership, add_user_group, remove_user_group
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
        logging.warning(f'processing {authorlist_inst} {keycloak_group}')
        authorlist_users = [a for a in state.authors(now) if authorlist_inst in a['instnames']]

        # 1) is the user in the regular institution group?
        group = '/'.join(keycloak_group.split('/')[:-1])
        keycloak_users = await get_keycloak_users(group, rest_client=client)

        matches = match_users(authorlist_users, keycloak_users)

        # 2) is the user anywhere in Keycloak?
        for author in authorlist_users:
            for au,ku in matches:
                if author == au:
                    break
            else:
                author_username = make_username(author)[1:]
                extra_matches = []
                if len(author_username) > 3:
                    ret = await list_users(search=author_username, rest_client=client)
                    for username in ret:
                        if match_one(author, ret[username]):
                            extra_matches.append(ret[username])
                if len(extra_matches) != 1:
                    ret = await list_users(search=author['email'].split('@')[0].split('.')[-1], rest_client=client)
                    for username in ret:
                        if match_one(author, ret[username]):
                            extra_matches.append(ret[username])
                if len(extra_matches) == 1:
                    matches.append((author, extra_matches[0]))
                    continue

                logging.warning(f'   authorlist extra user: {author["first"]} {author["last"]} {author["email"]}')

        #keycloak_extra = sorted({k['username'] for k in keycloak_users} - {ku['username'] for au,ku in matches})
        #if keycloak_extra:
        #    logging.info(f'keycloak extra users: {keycloak_extra}')

        # 3) update Keycloak author list group
        # ~ members = await get_group_membership(keycloak_group, rest_client=client)
        # ~ for au,ku in matches:
            # ~ if ku['username'] not in members:
                # ~ logging.warning(f'   adding {ku["username"]}')
                # ~ await add_user_group(keycloak_group, ku["username"], rest_client=client)
        # ~ for member in members:
            # ~ for au,ku in matches:
                # ~ if ku['username'] == member:
                    # ~ break
            # ~ else:
                # ~ logging.warning(f'   removing {member}')
                # ~ await remove_user_group(keycloak_group, member, rest_client=client)

        # 4) check user attribute for author name
        for au,ku in matches:
            attrs = ku.get('attributes', {}).copy()
            ku_name = attrs.get('author_name', '')
            update = False
            if au['authname'] != ku_name:
                attrs['author_name'] = au['authname']
                update = True
            if au['orcid'] != attrs.get('orcid', ''):
                attrs['orcid'] = au['orcid']
                update = True
            if au['thanks'] != attrs.get(f'authorlist_{experiment.lower()}_thanks', []):
                attrs[f'authorlist_{experiment.lower()}_thanks'] = au['thanks']
                update = True
            if update:
                logging.warning(f'  updating attribs for {ku["username"]}')
                await modify_user(ku['username'], attrs, rest_client=client)



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
