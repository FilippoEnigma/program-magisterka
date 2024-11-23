from setuptools import setup
import os

# Upewnij się, że pracujesz w katalogu, w którym znajduje się setup.py
base_dir = os.path.dirname(__file__)
templates_dir = os.path.join(base_dir, 'templates')

setup(
    name='magisterka',
    version='1.0.0',
    description='Aplikacja Flask do zarządzania wydarzeniami i płatnościami.',
    author='Filip',
    author_email='your.email@example.com',
    py_modules=['app'],  # Zakłada, że `app.py` to główny plik aplikacji
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
        '': ['templates/*.html'],  # Uwzględnij pliki HTML w katalogu templates
    },
)
