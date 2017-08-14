ansible_kernel
======================

ansible kernel for jupyter

Tested under max osx 10.12 with ansible 2.3.X.

1. read hosts file from '/usr/local/etc/ansible/hosts'
    ```
    [tf]
    192.168.X.XXX ansible_python_interpreter="/usr/bin/env python3" ansible_ssh_user=remote_user_name ansible_become_pass=remote_user_password
    
    [local]
    localhost              ansible_connection=local
    ```
    tf and local group in hosts file, and input follow to show 'hello world' on to machine.
    ```$ansible
    hosts: tf, local
    tasks:
      - debug: msg="hello world"
    ``` 

2. human readable output
    ```
    TASK [localhost: TASK: Gathering Facts] 
    
    
    TASK [192.168.10.238: TASK: Gathering Facts] 
    
    
    TASK [192.168.10.238: TASK: debug] 
    hello world
    
    TASK [localhost: TASK: debug] 
    hello world
    
    ok
    ```

3. default hosts is localhost
    ```
    - debug: msg="hello world"
    - shell: ls -l
    ```
    output:
    ```
    TASK [localhost: TASK: Gathering Facts] 
    
    
    TASK [localhost: TASK: debug] 
    hello world
    
    TASK [localhost: TASK: command] 
    stdout:
    total 24
    drwxr-xr-x  4 mind  staff   136 Aug 11 18:01 2017
    -rw-r--r--  1 mind  staff   830 Aug 11 23:48 Untitled.ipynb
    -rw-r--r--  1 mind  staff  1090 Aug 14 16:32 Untitled1.ipynb
    stderr:
    
    
    ok
    ```

4. set gather_facts to false could skip 'Gathering Facts'
    ```
    hosts: tf
    gather_facts: no
    tasks:
        - debug: msg="hello world"
    ```
    output:
    ```
    TASK [192.168.10.238: TASK: debug] 
    hello world
    
    ok
    ```

Usage
-----

    $ pip install -e .
    $ python -m ansible_kernel.install --sys-prefix
