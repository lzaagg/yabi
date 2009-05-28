from yabiadmin import settings
from yabiadmin.ldapclient import LDAPClient

def get_all_users():
    ldapclient = LDAPClient(settings.AUTH_LDAP_SERVERS)
    filter = "(objectclass=person)"
    result = ldapclient.search(settings.AUTH_LDAP_BASE, filter)

    return dict(result)

def get_yabi_userids():
    ldapclient = LDAPClient(settings.AUTH_LDAP_SERVERS)
    filter = "(cn=%s)" % settings.AUTH_LDAP_USER_GROUP
    result = ldapclient.search(settings.AUTH_LDAP_GROUP_BASE, filter, [ 'uniqueMember'] )
    return set(result[0][1]['uniqueMember'])
      
def get_userdn_of(username):
    ldapclient = LDAPClient(settings.AUTH_LDAP_SERVERS)
    userfilter = "(&(objectclass=person) (uid=%s))" % username
    result = ldapclient.search(settings.AUTH_LDAP_BASE, userfilter, ['dn'])
    if result and len(result) == 1:
        return result[0][0]

def can_bind_as(userdn, password):
    ldapclient = LDAPClient(settings.AUTH_LDAP_SERVERS)
    try:
        if ldapclient.bind_as(userdn, password):
            return True
    finally:
        ldapclient.unbind()

def is_user_member_of(userdn, groupname):
    ldapclient = LDAPClient(settings.AUTH_LDAP_SERVERS)
    groupfilter = '(&(objectClass=groupofuniquenames)(uniqueMember=%s)(cn=%s))' % (userdn, groupname)
    result = ldapclient.search(settings.AUTH_LDAP_GROUP_BASE, groupfilter, ['cn'])
    return len(result) == 1

