from setuptools import setup


setup(
    name='teeworlds-apiserver',
    url='https://github.com/Jakski/teeworlds-apiserver',
    author='Jakub Pieńkowski',
    author_email='jakub@jakski.name',
    license='MIT',
    description='Teeworlds HTTP API server for reading and submitting events',
    version='0.0.1',
    packages=['teeworlds_apiserver'],
    install_requires=[
        'aiohttp',
        'aiodns',
        'cchardet',
        'websockets',
    ],
    entry_points={
        'console_scripts': [
            'teeworlds-apiserver=teeworlds_apiserver:main'
        ]
    }
)
