from setuptools import setup, find_packages

setup(
    name='ckanext-bengkulusatudata',
    version='0.1',
    description='Plugin Bengkulu Satu Data',
    packages=find_packages(),
    namespace_packages=['ckanext'],
    include_package_data=True,
    entry_points='''
    [ckan.plugins]
    ckanext-bengkulusatudata=ckanext.bengkulusatudata.plugin:BengkuluSatuDataPlugin
    ''',
)