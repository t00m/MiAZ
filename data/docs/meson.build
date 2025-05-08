install_subdir('conf', install_dir: join_paths(get_option('datadir'), meson.project_name(), 'resources' ))
install_subdir('icons', install_dir: join_paths(get_option('datadir'), meson.project_name(), 'resources' ))
install_subdir('plugins', install_dir: join_paths(get_option('datadir'), meson.project_name(), 'resources' ))

pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
gnome = import('gnome')

gnome.compile_resources('miaz',
  'miaz.gresource.xml',
  gresource_bundle: true,
  install: true,
  install_dir: pkgdatadir,
)

