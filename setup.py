from setuptools import setup

setup(
    name='magisterka',
    version='1.0.0',
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
        'templates': ['*.html'],  # Uwzględnij wszystkie pliki HTML w templates
    },
)
