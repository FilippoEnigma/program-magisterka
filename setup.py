from setuptools import setup
import os

# Upewnij się, że pracujesz w katalogu, w którym znajduje się setup.py
base_dir = os.path.dirname(__file__)
templates_dir = os.path.join(base_dir, 'templates')

setup(
    name='magisterka',
    version='1.0.1',
    description='Aplikacja Flask do zarządzania wydarzeniami i płatnościami.',
    author='Filip',
    author_email='your.email@example.com',
    py_modules=['app'],  # Jeśli masz tylko `app.py`
    include_package_data=True,  # Wymaga MANIFEST.in do załączenia plików
    install_requires=[
        'flask',
        'configparser',
        'mysql-connector-python',
        'werkzeug',
        'wtforms',
    ],
    entry_points={
        'console_scripts': [
            'magisterka=app:main',  # Zmapowane na funkcję main w app.py
        ],
    },
    package_data={
        '': ['*.ini'],  # Uwzględnij pliki konfiguracyjne
    },
    data_files=[
        ('templates', [os.path.join('templates', f) for f in os.listdir(templates_dir) if f.endswith('.html')]),
    ],
)
