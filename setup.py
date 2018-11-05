from setuptools import setup

version = "0.1.0"

requirements = [
    'PyYAML',
    'requests',
    'voluptuous'
]

with open("README.md", "r") as f:
    readme = f.read()

setup(name='pkictl',
    version=version,
    description='A command-line utility for declaratively provisioning PKI in Hashicorp Vault',
    long_description=readme,
    long_description_content_type="text/markdown",
    url='http://github.com/bincyber/pkictl',
    author='@bincyber',
    license='AGPL',
    keywords="vault pki kubernetes public key infrastructure security",
    packages=['pkictl'],
    python_requires='>=3.6',
    platforms=['any'],
    install_requires=requirements,
    zip_safe=False,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Natural Language :: English',
        'License :: OSI Approved :: GNU Affero General Public License v3',
        'Operating System :: MacOS',
        'Operating System :: POSIX',
        'Operating System :: Unix',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Topic :: Security',
        'Topic :: Security :: Cryptography',
        'Topic :: System :: Systems Administration',
        'Topic :: Utilities'
    ],
    entry_points = {
        'console_scripts': ['pkictl=pkictl.pkictl:main']
    },
    test_suite='nose2.collector.collector',
    tests_require=['nose2']
)
