#
node default {
  include globals
  include ccgcommon
  include ccgcommon::source
  include ccgapache
  include python
  include repo::epel
  include repo::ius
  include repo::pgrpms
  include repo::ccgcentos

  $django_config = {
    deployment  => 'prod',
    release     => '7.2.4-1',
    dbdriver    => 'django.db.backends.postgresql_psycopg2',
    dbhost      => $globals::dbhost_rds_syd_postgresql_prod,
    dbname      => 'yabiadmin_prod',
    dbuser      => $globals::dbuser_syd_prod,
    dbpass      => $globals::dbpass_syd_prod,
    memcache    => $globals::memcache_syd,
    secret_key  => $globals::secretkey_yabi,
    admin_email => $globals::system_email,
  }

  $packages = ['python27-psycopg2', 'rabbitmq-server']
  package {$packages: ensure => installed}

  package {'yabi-admin': 
    ensure => $django_config['release'], 
    provider => 'yum_nogpgcheck'
  }

  django::config { 'yabiadmin':
    config_hash => $django_config,
  }

  # Disabled until releasing on this branch
  #django::syncdbmigrate{'yabiadmin':
  #  dbsync  => true,
  #  require => [
  #    Ccgdatabase::Postgresql[$django_config['dbname']],
  #    Package['yabi-admin'],
  #    Django::Config['yabiadmin'] ]
  #}

  package {'yabi-shell': provider => yum_nogpgcheck}

  service { 'rabbitmq-server':
    ensure     => 'running',
    enable     => true,
    hasstatus  => true,
    hasrestart => true,
    name       => 'rabbitmq-server',
    require    => Package[$packages]
  }

  # Disabled until releasing on this branch
  #service { 'celeryd':
  #  ensure     => 'running',
  #  enable     => true,
  #  hasstatus  => true,
  #  hasrestart => true,
  #  name       => 'celeryd',
  #  require    => [
  #    Service['rabbitmq-server'],
  #    Package[$packages],
  #    Ccgdatabase::Postgresql[$django_config['dbname']],
  #    Package['yabi-admin'] ]
  #}
}
