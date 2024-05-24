project('MiAZ',
          version: '0.0.25',
    meson_version: '>= 0.61.2',
  default_options: [ 'warning_level=2',
                   ],
)

python = import('python')
i18n = import('i18n')


profile = get_option('profile')
if profile == 'development'
  app_id = 'com.github.t00m.MiAZ.Devel'
  prefix = '/com/github/t00m/MiAZ/Devel'
elif profile == 'release'
  app_id = 'com.github.t00m.MiAZ'
  prefix = '/com/github/t00m/MiAZ'
endif

pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
moduledir = join_paths(pkgdatadir, 'MiAZ')

conf = configuration_data()
conf.set('PYTHON', python.find_installation('python3').full_path())
conf.set('PYTHON_VERSION', python.find_installation('python3').language_version())
conf.set('APP_ID', app_id)
conf.set('PREFIX', prefix)
conf.set('VERSION', meson.project_version())
#~ conf.set('REVISION', revision)
conf.set('PROFILE', profile)
conf.set('localedir', join_paths(get_option('prefix'), get_option('localedir')))
conf.set('pkgdatadir', pkgdatadir)

subdir('data')
subdir('MiAZ')
subdir('po')

meson.add_install_script('build-aux/meson/postinstall.py')
