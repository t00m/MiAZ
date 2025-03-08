# Generate MiAZ environment module
configure_file(
  input: 'env.in',
  output: 'env.py',
  configuration: conf,
  install: true,
  install_dir: moduledir
)

# Generate MiAZ binary module
configure_file(
  input: 'miaz.py',
  output: 'miaz',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir'),
  install_mode: 'rwxrwxr-x'
)

# Python sources
sources = []

install_data(sources, install_dir: moduledir)

# Subpackages
install_subdir('backend', install_dir: moduledir)
install_subdir('frontend', install_dir: moduledir)
