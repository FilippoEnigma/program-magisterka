from setuptools import setup, find_packages

setup(
    name='magisterka',
    version='1.0.0',
    description='Aplikacja Flask do zarządzania wydarzeniami i płatnościami.',
    author='Filip',
    author_email='your.email@example.com',
    packages=find_packages(),  # Jeśli masz katalog, lepiej użyć find_packages()
    include_package_data=True,  # Wymaga MANIFEST.in
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
        '': ['*.ini'],  # Uwzględnij pliki .ini
        'templates': ['*.html'],  # Uwzględnij pliki HTML w templates
    },
)
