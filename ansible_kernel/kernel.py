import traceback
import yaml
import json
import sys
import re

from ipykernel.kernelbase import Kernel
from collections import namedtuple

from ansible.errors import AnsibleParserError
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.inventory import Inventory
from ansible.parsing.dataloader import DataLoader
from ansible.playbook.play import Play
from ansible.vars import VariableManager
from ansible.release import __version__ as ansible_version
from ansible.plugins.callback import CallbackBase

from subprocess import check_output

__version__ = '0.1'


class UnknownInput(AnsibleParserError):
    """Error in shorthand syntaxes this kernel accepts."""
    # Not certain if this inheriting from AnsibleParserError is best, doesn't matter much.


class AnsibleKernel(Kernel, CallbackBase):
    implementation = 'ansible_kernel'
    implementation_version = __version__

    language = 'Ansible'
    language_version = ansible_version

    _banner = None

    result_output_format = {
        'ansible_facts': '',
        'msg': '{msg}',
        'cmd': 'stdout:\n{stdout}\nstderr:\n{stderr}',
        'invocation': 'changed: {changed}'
    }

    @property
    def banner(self):
        if self._banner is None:
            self._banner = check_output(['ansible', '--version']).decode('utf-8')
        return self._banner

    language_info = dict(
        name='ansible',
        # https://stackoverflow.com/questions/332129/yaml-mime-type
        # Actually text/vnd.yaml was proposed but the proposal hasn't advanced.
        mimetype='text/vnd.yaml',
        file_extension='.yml',
        codemirror_mode='yaml',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        Options = namedtuple('Options',
                             ['listtags', 'listtasks', 'listhosts', 'syntax', 'connection', 'module_path', 'forks',
                              'remote_user', 'private_key_file', 'ssh_common_args', 'ssh_extra_args', 'sftp_extra_args',
                              'scp_extra_args', 'become', 'become_method', 'become_user', 'become_pass', 'verbosity',
                              'check'])
        self.options = Options(listtags=False, listtasks=False, listhosts=False, syntax=False, connection='ssh',
                               module_path=None, forks=100, remote_user=None, private_key_file=None,
                               ssh_common_args=None, ssh_extra_args=None, sftp_extra_args=None, scp_extra_args=None,
                               become=False, become_method='sudo', become_user='root', become_pass=None, verbosity=None,
                               check=False)

        self.variable_manager = VariableManager()
        self.loader = DataLoader()
        self.inventory = Inventory(loader=self.loader, variable_manager=self.variable_manager,
                                   host_list='/usr/local/etc/ansible/hosts')
        self.passwords = {}

        self._options = {'hosts': {'type': str, 'val': 'localhost'},
                         'showDetail': {'type': bool, 'val': False}}

    def task_queue_manager(self):
        return TaskQueueManager(
            inventory=self.inventory,
            variable_manager=self.variable_manager,
            loader=self.loader,
            options=self.options,
            passwords=self.passwords,
            stdout_callback=self,
        )

    def get_result_output(self, result):
        if not self._options['showDetail']['val']:
            for key, out_format in self.result_output_format.items():
                if key in result:
                    return out_format.format(**result)

        return json.dumps(result, indent=2)

    def v2_runner_on_ok(self, result, **kwargs):
        """Print a json representation of the result

        This method could store the result in an instance attribute for retrieval later
        """
        try:
            stream_content = {'name': 'stdout', 'text':
                'TASK [{0}: {1}] \n{2}\n\n'.format(result._host, result._task, self.get_result_output(result._result))}
            self.send_response(self.iopub_socket, 'stream', stream_content)
        except:
            self.log.error(sys.exc_info()[0])

    def parser_comments_from_code(self, code):
        if code.lstrip().find('#') == 0:
            code = code.splitlines()[0]
            m = re.findall('[^# =]+ *= *[^=]+(?: +|$)(?! *=)', code)
            if m:
                for kv in m:
                    k, v = kv.split('=')
                    if k.strip() in self._options:
                        self._options[k.strip()]['val'] = self._options[k.strip()]['type'](v.strip())
                        self.send_response(self.iopub_socket, 'stream',
                                           {'name': 'stdout',
                                            'text': 'Set hosts to: {0}\n'.format(self._options['hosts']['val'])})
                        return True

    def play_from_code(self, code):
        parsered = self.parser_comments_from_code(code)
        """Support one task, list of tasks, or whole play without hosts."""
        data = orig_data = yaml.safe_load(code)
        if isinstance(data, dict) and 'tasks' not in data:
            data = [data]
        if isinstance(data, list):
            data = dict(tasks=data)
        if not isinstance(data, dict):
            if parsered:
                return
            else:
                raise UnknownInput("Expected task, list of tasks, or play, got {}".format(type(orig_data)))
        if 'hosts' not in data:
            data['hosts'] = self._options['hosts']['val']
            self.send_response(self.iopub_socket, 'stream',
                               {'name': 'stdout',
                                'text': 'Use hosts: {0}\n'.format(self._options['hosts']['val'])})

        return Play.load(data, self.variable_manager, self.loader)

    def do_execute(self, code, silent, store_history=True, user_expressions=None, allow_stdin=False):
        try:
            ret = self.task_queue_manager().run(self.play_from_code(code))
        except (yaml.YAMLError, AnsibleParserError) as e:
            message = ''.join(traceback.format_exception_only(type(e), e))
            stream_content = {'name': 'stderr', 'text': message}
        else:
            if ret == 0:
                stream_content = {'name': 'stdout', 'text': 'ok'}
            else:
                stream_content = {'name': 'stderr', 'text': 'error: {0}'.format(ret)}

        if not silent:
            self.send_response(self.iopub_socket, 'stream', stream_content)

        return {'status': 'ok',
                # The base class increments the execution count
                'execution_count': self.execution_count,
                'payload': [],
                'user_expressions': {},
                }
