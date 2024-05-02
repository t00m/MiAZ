configure_file(
  input: 'miaz.py',
  output: 'miaz',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir'),
  install_mode: 'r-xr--r--'
)

# Python sources
sources = [
#~   'main.py',
]

install_data(sources, install_dir: moduledir)

# Subpackages
install_subdir('backend', install_dir: moduledir)
install_subdir('frontend', install_dir: moduledir)
