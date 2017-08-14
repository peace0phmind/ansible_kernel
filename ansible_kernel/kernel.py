import traceback
import yaml
import json
import sys

from ipykernel.kernelbase import Kernel
from collections import namedtuple

from ansible.cli import CLI
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
        'cmd': 'stdout:\n{stdout}\nstderr:\n{stderr}'
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
                             ['connection', 'module_path', 'forks', 'become', 'become_method', 'become_user', 'check'])
        self.options = Options(connection='local', module_path='', forks=100, become=None, become_method=None,
                               become_user=None, check=False)

        self.variable_manager = VariableManager()
        self.loader = DataLoader()
        self.inventory = Inventory(loader=self.loader, variable_manager=self.variable_manager,
                                   host_list='/usr/local/etc/ansible/hosts')
        self.passwords = dict(vault_pass='secret')

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
        for key, out_format in self.result_output_format.items():
            if key in result:
                return out_format.format(**result)

        return json.dumps(result, indent=2)

    def v2_runner_on_ok(self, result, **kwargs):
        """Print a json representation of the result

        This method could store the result in an instance attribute for retrieval later
        """
        self.log.error(result._result)

        try:
            stream_content = {'name': 'stdout', 'text':
                'TASK [{0}: {1}] \n{2}\n\n'.format(result._host, result._task, self.get_result_output(result._result))}
            self.send_response(self.iopub_socket, 'stream', stream_content)
        except:
            self.log.error(sys.exc_info()[0])

    def play_from_code(self, code):
        """Support one task, list of tasks, or whole play without hosts."""
        data = orig_data = yaml.safe_load(code)
        if isinstance(data, dict) and 'tasks' not in data:
            data = [data]
        if isinstance(data, list):
            data = dict(tasks=data)
        if not isinstance(data, dict):
            raise UnknownInput("Expected task, list of tasks, or play, got {}".format(type(orig_data)))
        if 'hosts' not in data:
            data['hosts'] = 'localhost'
        self.log.error(data)
        return Play.load(data, self.variable_manager, self.loader)

    def do_execute(self, code, silent, store_history=True, user_expressions=None, allow_stdin=False):
        try:
            ret = self.task_queue_manager().run(self.play_from_code(code))
            self.log.error("{}".format(ret))
        except (yaml.YAMLError, AnsibleParserError) as e:
            message = ''.join(traceback.format_exception_only(type(e), e))
            stream_content = {'name': 'stderr', 'text': message}
        else:
            stream_content = {'name': 'stdout', 'text': 'ok'}
            # stream_content = {'name': 'stdout', 'text': ret}
            # self.send_response(self.iopub_socket, 'stream', stream_content)

        if not silent:
            self.send_response(self.iopub_socket, 'stream', stream_content)

        return {'status': 'ok',
                # The base class increments the execution count
                'execution_count': self.execution_count,
                'payload': [],
                'user_expressions': {},
                }
