from setuptools import setup, find_packages

setup(
    name='magisterka',
    version='1.0.0',
    description='Aplikacja Flask do zarządzania wydarzeniami i płatnościami.',
    author='Filip',
    author_email='your.email@example.com',
    py_modules=['app'],
    include_package_data=True,
    install_requires=[
        'flask',
        'configparser',
        'mysql-connector-python',
        'werkzeug',
        'wtforms',
    ],
    entry_points={
        'console_scripts': [
            'magisterka=app:main',
        ],
    },
    packages=find_packages(),  # Użyj tego, jeśli masz strukturę katalogów jako paczki
    package_data={
        '': ['*.ini', 'templates/*.html'],  # Uwzględnij wszystkie pliki w templates
    },
)
