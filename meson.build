project('miaz',
    version: '0.1',
    meson_version: '>= 0.59.0'
)

# Importing modules
gnome = import('gnome')
i18n  = import('i18n')
python = import('python')

# Module objects
py_installation = python.find_installation('python3')

# Make sure Python is installed and found
if not py_installation.found()
    error('No valid python3 binary found')
endif

# Python 3.7 is needed for postponed evalution of annotations
if not py_installation.language_version().version_compare('>= 3.7')
  error('Python 3.7 or newer is required.')
endif

# Constants
PACKAGE_URL = 'https://github.com/t00m/MiAZ'
PACKAGE_URL_BUG = 'https://github.com/t00m/MiAZ/issues'
PROJECT_RDNN_NAME = 'com.github.t00m.MiAZ'

# NAME_SUFFIX is used in the about dialog
if get_option('profile') == 'development'
  PROFILE = '.Devel'
  NAME_SUFFIX = ' (Development Snapshot)'
else
  PROFILE = ''
  NAME_SUFFIX = ''
endif

APPLICATION_ID = 'com.github.t00m.MiAZ@0@'.format(PROFILE)
PYTHON_DIR = py_installation.get_path('purelib')
PKGDATA_DIR = join_paths(get_option('prefix'), get_option('datadir'), APPLICATION_ID)
PKGLIB_DIR = join_paths(get_option('prefix'), get_option('libdir'), APPLICATION_ID)
VCS_TAG = ''
if get_option('profile') != 'default'
  git = find_program('git', required : false)
  if git.found()
    VCS_TAG = run_command('git', 'rev-parse', '--short', 'HEAD').stdout().strip()
  endif
  if VCS_TAG == ''
    VCS_TAG = '-devel'
  else
    VCS_TAG = '-@0@'.format(VCS_TAG)
  endif
endif


# Dependencies
dependency('glib-2.0', version: '>= 2.67.1')
dependency('gobject-introspection-1.0', version: '>= 1.35.0')
dependency('gtk4', version: '>= 4.6.0')
dependency('libadwaita-1', version: '>= 1.2.alpha')
dependency('pygobject-3.0', version: '>= 3.36.1')
dependency('libpeas', version: '1.32.0')

subdir('data')
#~ subdir('help')
subdir('po')

install_subdir(
    'MiAZ',
    install_dir: py_installation.get_install_dir()
)

# Install the executable file
bin_config = configuration_data()
bin_config.set('application_id', APPLICATION_ID)
bin_config.set('rdnn_name', PROJECT_RDNN_NAME)
bin_config.set('pkgdatadir', PKGDATA_DIR)
bin_config.set('localedir', join_paths(get_option('prefix'), get_option('datadir'), 'locale'))
bin_config.set('pythondir', PYTHON_DIR)
bin_config.set('schemasdir', PKGDATA_DIR)
bin_config.set('version', meson.project_version() + VCS_TAG)

bin_config.set('local_build', 'False')

configure_file(
    input: 'miaz.in',
    output: 'miaz',
    configuration: bin_config,
    install_dir: get_option('bindir')
)

# Install the builddir executable
local_config = configuration_data()
local_config.set('application_id', APPLICATION_ID)
local_config.set('rdnn_name', PROJECT_RDNN_NAME)
local_config.set('pkgdatadir', join_paths(meson.current_build_dir(), 'data'))
local_config.set('localedir', join_paths(get_option('prefix'), get_option('datadir'), 'locale'))
local_config.set('pythondir', meson.current_source_dir())
local_config.set('schemasdir', join_paths(meson.current_build_dir(), 'data'))

local_config.set('local_build', 'True')

configure_file(
    input: 'miaz.in',
    output: 'local-miaz',
    configuration: local_config
)

gnome.post_install(
    glib_compile_schemas: true,
    gtk_update_icon_cache: true,
    update_desktop_database: true
)
