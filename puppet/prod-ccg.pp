#
node default {
  include globals
  include ccgcommon
  include ccgcommon::source
  include ccgapache
  include python
  include repo
  include repo::repo::ius
  include repo::repo::ccgcentos
  include repo::repo::ccgdeps
  class { 'yum::repo::pgdg93':
    stage => 'setup',
  }
  include globals
  include profile::rsyslog

  $django_config = {
    deployment                   => 'prod',
    release                      => '9.6.0-1',
    dbdriver                     => 'django.db.backends.postgresql_psycopg2',
    dbserver                     => $globals::dbhost_postgresql_ccg_prod,
    dbhost                       => $globals::dbhost_postgresql_ccg_prod,
    dbname                       => 'live_yabi',
    dbuser                       => $globals::dbuser_postgresql_ccg_prod,
    dbpass                       => $globals::dbpass_postgresql_ccg_prod,
    memcache                     => $globals::memcache_ccg_prod,
    auth_type                    => 'ldap',
    auth_ldap_server             => $globals::ldap_ccg_prod,
    auth_ldap_user_base          => $globals::ldap_ccg_prod_user_base,
    auth_ldap_group_dn           => 'cn=yabi, ou=Yabi,ou=Web Groups,dc=ccg,dc=murdoch,dc=edu,dc=au',
    auth_ldap_admin_group_dn     => 'cn=admin, ou=Yabi,ou=Web Groups,dc=ccg,dc=murdoch,dc=edu,dc=au',
    auth_ldap_require_TLS_cert   => false,
    auth_ldap_sync_user_on_login => true,
    secret_key                   => $globals::secretkey_ccg_yabi,
    admin_email                  => $globals::system_email,
    allowed_hosts                => '.ccg.murdoch.edu.au localhost',
    torque_path                  => '/opt/torque/2.3.13/bin',
    sge_path                     => '/opt/sge6/bin/linux-x64',
    aws_access_key_id            => $globals::yabi_aws_access_key_id,
    aws_secret_access_key        => $globals::yabi_aws_secret_access_key,
  }

  $packages = ['python27-psycopg2', 'rabbitmq-server']
  package {$packages: ensure => installed}

  package {'yabi-admin':
    ensure => $django_config['release'],
    provider => 'yum_nogpgcheck'
  }

  package {'yabi-shell':
    ensure => $django_config['release'],
    provider => 'yum_nogpgcheck'
  }

  django::config { 'yabi':
    config_hash => $django_config,
  }

  # Disabled until releasing on this branch
  django::syncdbmigrate{'yabi':
    dbsync  => true,
    require => [
      Package['yabi-admin'],
      Django::Config['yabi'] ]
  }

  service { 'rabbitmq-server':
    ensure     => 'running',
    enable     => true,
    hasstatus  => true,
    hasrestart => true,
    name       => 'rabbitmq-server',
    require    => Package[$packages]
  }

  # Disabled until releasing on this branch
  service { 'celeryd':
    ensure     => 'running',
    enable     => true,
    hasstatus  => true,
    hasrestart => true,
    name       => 'celeryd',
    require    => [
      Service['rabbitmq-server'],
      Package[$packages],
      Package['yabi-admin'] ]
  }

  logrotate::rule { 'celery':
    path          => '/var/log/celery/*log',
    rotate        => 7,
    rotate_every  => 'day',
    compress      => true,
    delaycompress => true,
    ifempty       => true,
    create        => true,
    create_mode   => '0664',
    create_owner  => 'celery',
    create_group  => 'celery',
  }
}
