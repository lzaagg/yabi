#
node default {
  include ccgcommon
  include ccgcommon::source
  include ccgapache
  include python
  include repo::epel
  include repo::ius
  include repo::pgrpms
  include repo::ccgtesting
  include globals
  include ccgdatabase::postgresql::devel

  # There are some leaked local secrets here we don't care about
  $django_config = {
    deployment  => 'staging',
    dbdriver    => 'django.db.backends.postgresql_psycopg2',
    dbhost      => '',
    dbname      => 'yabi_staging',
    dbuser      => 'yabi',
    dbpass      => 'yabi',
    memcache    => $globals::memcache_syd,
    secret_key  => 'isbfiusbef)#$)(#)((@',
    admin_email => $globals::system_email,
    allowed_hosts => 'localhost',
  }

  $packages = ['python27-psycopg2', 'rabbitmq-server']
  package {$packages: ensure => installed}

  # tests need firefox and a virtual X server
  $testingpackages = ['firefox', 'xorg-x11-server-Xvfb', 'dbus-x11']
  package {$testingpackages:
    ensure => installed,
  }

  # fakes3 is required for tests
  package {'fakes3':
    ensure     => installed,
    provider   => gem
  }

  # TODO Need to port this across
  # drop in auth details for e2e tests
  #file {'/usr/local/src/yabi':
  #  ensure => directory
  #} ->
  #file {'/usr/local/src/yabi/staging_tests.conf':
  #  source => 'puppet:///modules/staging/yabi_staging_tests.conf'
  #}

  ccgdatabase::postgresql::db { $django_config['dbname']:
    user     => $django_config['dbuser'],
    password => $django_config['dbpass'],
  }

  package {'yabi-admin': ensure => installed, provider => 'yum_nogpgcheck'}

  django::config { 'yabiadmin':
    config_hash => $django_config,
  }

  django::syncdbmigrate{'yabiadmin':
    dbsync  => true,
    notify  => Service[$ccgapache::params::service_name],
    require => [
      Ccgdatabase::Postgresql::Db[$django_config['dbname']],
      Package['yabi-admin'],
      Django::Config['yabiadmin'] ]
  }

  package {'yabi-shell': provider => yum_nogpgcheck}

  service { 'rabbitmq-server':
    ensure     => 'running',
    enable     => true,
    hasstatus  => true,
    hasrestart => true,
    name       => 'rabbitmq-server',
    require    => Package[$packages]
  }

  service { 'celeryd':
    ensure     => 'running',
    enable     => true,
    hasstatus  => true,
    hasrestart => true,
    name       => 'celeryd',
    require    => [
      Service['rabbitmq-server'],
      Package[$packages],
      Ccgdatabase::Postgresql::Db[$django_config['dbname']],
      Package['yabi-admin'],
      Django::Config['yabiadmin'] ]
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