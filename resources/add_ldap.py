import json
import itertools

import unidecode
import ldap3


LDAP_URI = 'ldaps://ldap-1.icecube.wisc.edu'
LDAP_USER_BASE = 'ou=People,dc=icecube,dc=wisc,dc=edu'
LDAP_GROUP_BASE = 'ou=Group,dc=icecube,dc=wisc,dc=edu'
LDAP_INST_BASE = 'ou=Institutions,dc=icecube,dc=wisc,dc=edu'


def get_ldap(username):
    conn = ldap3.Connection(LDAP_URI, auto_bind=True)
    #ret = conn.search(LDAP_INST_BASE, f'(objectClass=i3institution)', attributes=ldap3.ALL_ATTRIBUTES)
    #insts = {}
    #for entry in conn.entries:
    #    data = entry.entry_attributes_as_dict
    #    insts[data['o'][0]] = data['cn'][0]
    #print(insts)

    ret = conn.search(LDAP_USER_BASE, f'(&(objectClass=i3Person)(uid={username}))', attributes=ldap3.ALL_ATTRIBUTES)
    if not ret:
        raise Exception('bad username')
    ret = []
    for entry in conn.entries:
        try:
            data = entry.entry_attributes_as_dict
            #print(data)
            ret.append({
                'first': data['givenName'][0],
                'last': data['sn'][0],
                'email': data['mail'][0] if 'email' in data else data['uid'][0]+'@icecube.wisc.edu',
                #'inst': insts[data['o'][0].split(',')[0].split('=')[-1]],
            })
        except:
            print('bad',data['uid'])
            raise
    return ret

def get_maillist(filename='icecube-p.txt'):
    ret = []
    with open(filename) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            ret.append(line)
    return ret

def main():
    with open('output.json') as f:
        data = json.load(f)

    ldap_data = get_ldap('*')
    email_data = get_maillist('icecube-c.txt')
    email_data2 = get_maillist('icecube-p.txt')

    for a in data['authors']:
        if 'email' in a:
            continue
        anames = [unidecode.unidecode(a['authname']).replace("'",'').lower()]
        authname = a['authname'].replace('ü','ue').replace('ö','oe')
        anames.append(unidecode.unidecode(authname).replace("'",'').lower())

        for aname in anames:
            # first try email lists
            for email in itertools.chain(email_data, email_data2):
                parts = aname.split('. ')
                alast = parts[-1].split(' ')[-1]
                alast2 = parts[-1].replace(' ','')
                e = email.split('@')[0]
                if '.' in e:
                    elast = e.split('.')[1]
                    if len(elast) > 3 and (alast.startswith(elast) or alast2 == elast) and e[0] == aname[0]:
                        a['first'] = e.split('.')[0].capitalize()
                        a['email'] = email
                        break
                    elast = e.split('.')[-1]
                    if len(elast) > 3 and (alast.startswith(elast) or alast2 == elast) and e[0] == aname[0]:
                        a['first'] = e.split('.')[0].capitalize()
                        a['email'] = email
                        break
                    elast = ''.join(e.split('.')[1:])
                    if len(elast) > 3 and alast2 == elast and e[0] == aname[0]:
                        a['first'] = e.split('.')[0].capitalize()
                        a['email'] = email
                        break
                else:
                    elast = e[1:]
                    if len(elast) > 3 and alast.startswith(elast) and e[0] == aname[0]:
                        a['email'] = email
                        break

                    elast = e
                    if elast == alast:
                        a['email'] = email
                        break
            

            # now try ldap
            if 'email' not in a:
                for l in ldap_data:
                    name = l['first'][0]+'. '+l['last'].lower()
                    if aname == name:
                        break
                    name = l['first'][0]+'. '+l['last'].replace(' ','-').lower()
                    if aname == name:
                        break
                    parts = aname.split('. ')
                    if parts[-1] == l['last'].lower() and parts[0][0] == l['first'][0].lower():
                        break
                else:
                    continue
                a['first'] = l['first']
                a['email'] = l['email']

        # now fix up last name
        parts = a['authname'].rsplit('. ',1)
        if 'first' not in a:
            a['first'] = parts[0]+'.'
        a['last'] = parts[-1]

        if 'email' not in a:
            if a['to']:
                print('missing', a['authname'], a['instnames'])
            else:
                print('*** missing', a['authname'], a['instnames'])

    with open('output2.json', 'w') as f:
        json.dump(data, f, indent=2, sort_keys=True)


if __name__ == '__main__':
    main()
