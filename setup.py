from setuptools import setup

with open('README.md') as f:
    readme = f.read()

setup(
    name='ansible_kernel',
    version='0.1.1',
    description='An Ansible kernel for Jupyter',
    long_description=readme,
    author='peace0phmind',
    author_email='peace0phmind@gmail.com',
    url='https://github.com/peace0phmind/ansible_kernel',
    license='BSD 3-Clause License',
    classifiers=[
        'Programming Language :: Python :: 3',
    ],

    install_requires=[
        'ansible',
        'ipykernel',
        'jupyter_client >= 5.0.0',
    ],

    py_modules=['ansible_kernel'],
    data_files=["ansible_kernel/*"],
)
