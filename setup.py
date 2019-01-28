from setuptools import setup

requirements = [
    'PyQt5', 'paramiko'  # TODO: put your package requirements here
]

test_requirements = [
    'pytest',
    'pytest-cov',
    'pytest-faulthandler',
    'pytest-mock',
    # 'pytest-qt',
    'pytest-xvfb',
]

setup(
    name='chainup',
    version='0.0.1',
    description="A blockchain deployment tool.",
    author="get-set",
    author_email='535993116@qq.com',
    url='https://github.com/get-set/chainup',
    packages=['chainup', 'chainup.ui',
              'chainup.tests'],
    package_data={'chainup.ui.images': ['*.png']},
    entry_points={
        'console_scripts': [
            'chainup=chainup.main:main'
        ]
    },
    install_requires=requirements,
    zip_safe=False,
    keywords='chainup',
    classifiers=[
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    test_suite='tests',
    tests_require=test_requirements
)
