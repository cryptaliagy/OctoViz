from setuptools import setup, find_packages


setup(
    name='octoviz',
    author='Natalia Maximo',
    packages=find_packages('src'),
    package_dir={'':'src'},
    install_requires=[
        'github3.py',
        'bokeh',
        'arrow',
        'pandas'
    ],
    version='1.3.1',
    entry_points='''
        [console_scripts]
        octoviz=octoviz:cli
    '''
)