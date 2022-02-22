import asyncio
from datetime import datetime
import logging
from pprint import pprint

from krs.token import get_rest_client
from krs.users import list_users
from krs.institutions import list_insts
from authorlist.state import State

inst_mapping = {
    'atlanta': 'clark-atlanta',
    'anchorage': 'alaska-anchorage',
    'arlington': 'texas-arlington',
    'bartol': 'delaware',
    'berkeley': 'uc-berkeley',
    'brusselslibre': 'brussels-ulb',
    'brusselsvrije': 'brussels-vub',
    'chiba2022': 'chiba',
    'chicagoastro': 'chicago-astro',
    'chicagofermi': 'chicago-fermi',
    'chicagokavli': 'chicago-kavli',
    'chicagophysics': 'chicago-physics',
    'christchurch': 'canterbury',
    'edmonton': 'alberta',
    'georgia': 'gatech',
    'irvine': 'uc-irvine',
    'karlsruhe': 'karlsruhe-astro',
    'karlsruheexp': 'karlsruhe-exp',
    'madisonastro': 'uw-madison-astro',
    'madisonpac': 'uw-madison-wipac',
    'michigan': 'michigan-state',
    'ohio': 'ohio-state-physics',
    'ohioastro': 'ohio-state-astro',
    'pennastro': 'penn-state-astro',
    'pennphys': 'penn-state-physics',
    'penncosmos': 'penn-state-cosmos',
    'riverfalls': 'uw-river-falls',
    'sinica': 'academiasinica',
    'skku': 'sungkyunkwan-physics',
    'skku2': 'sungkyunkwan-basic-science',
    'southdakota': 'sd-mines-tech',
    'stockholmokc': 'stockholm',
    'stonybrook': 'stony-brook',
    'zeuthen': 'desy',
}

async def export(state, experiment, dryrun=False, client=None):
    now = datetime.utcnow().isoformat()
    print(now)
    authors = state.authors(now)
    author_insts = state.institutions(now)

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
    

    print('author insts:')
    mapping = {}
    for i in sorted(author_insts):
        if i in inst_mapping:
            if not inst_mapping[i]:
                print(i)
            else:
                mapping[i] = inst_mapping[i]
        elif i in krs_insts:
            mapping[i] = i
        else:
            print(i)

    print('----')
    print('keycloak insts:')
    for i in sorted(krs_insts):
        if i in mapping.values():
            continue
        else:
            print(i)

    #print(sorted(author_insts))
    #pprint(krs_insts_raw)

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
