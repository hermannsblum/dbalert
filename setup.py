from setuptools import setup

setup(
    name='dbalert',
    version='1.0.0',
    py_modules=['dbalert'],
    install_requires=[
        'requests',
        'python-dateutil',
        'Click',
    ],
    entry_points={
        'console_scripts': ['dbalert = dbalert:cli',],
    },
)
