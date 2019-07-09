from setuptools import setup


setup(
    name='octoviz',
    py_modules=['octoviz'],
    install_requires=[
        'github3.py',
        'bokeh',
        'arrow',
        'pandas'

    ],
    version='1.1',
    entry_points='''
        [console_scripts]
        octoviz=octoviz:cli
    '''
)