from typing import List, Dict, Any
from mcdreforged.api.utils.serializer import Serializable

# default_config = {
#   'debug': False,
#   'enabled': False,
#   'git_path': 'git',
#   'git_cfg': {
#     'use_remote': False,
#     'remote': 'https://github.com/user/repo.git',
#     'remote_name': 'origin',
#     'branch_name': 'main',
#     'is_setup': False,
#     'user_email': 'GitBackup@host.local',
#     'user_name': 'GitBackup',
#     'ssh_command': '',
#   },
#   'backup_interval': 60 * 60 * 24, # 1 day
#   'last_backup_time': 0,
#   'push_interval': 60 * 60 * 24, # 1 day
#   'last_push_time': 0,
#   'back_wait_time': 15,
#   'backup_path': './git_backup',
#   'cache_path': './git_backup_cache',
#   'server_path': './server',
#   'helper_count': 1,
#   'need_backup': [
#     'world',
#   ],
#   'ignores': [
#     'session.lock',
#   ],
#   # 0:guest 1:user 2:helper 3:admin 4:owner
#   'minimum_permission_level': {
#     'help':    1,
#     'status':  1,
#     'list':    1,
#     'make':    1,
#     'back':    2,
#     'confirm': 1,
#     'abort':   1,
#     'reload':  2,
#     'save':    2,
#     'push':    3,
#     'pull':    3
#   },
# }

class Configure(Serializable):
  debug: bool = True
  enabled: bool = False
  turn_off_auto_save: bool = True
  git_path: str = 'git'
  git_cfg: Dict[str, Any] = {
    'use_remote': False,
    'remote': 'git@github.com:user/repo.git',
    'remote_name': 'origin',
    'branch_name': 'main',
    'is_setup': False,
    'user_email': 'GitBackup@host.local',
    'user_name': 'GitBackup',
    'ssh_command': '',
  }
  backup_interval: int = 60 * 60 * 24 # 1 day
  last_backup_time: int = 0
  push_interval: int = 60 * 60 * 24 # 1 day
  last_push_time: int = 0
  back_wait_time: int = 15
  backup_path: str = './git_backup'
  cache_path: str = './git_backup_cache'
  server_path: str = './server'
  # helper_count: int = 1
  need_backup: List[str] = [
    'world',
  ]
  ignores: List[str] = [
    'session.lock',
  ]
  # 0:guest 1:user 2:helper 3:admin 4:owner
  minimum_permission_level: Dict[str, int] = {
    'help':    0,
    'status':  1,
    'list':    1,
    'make':    1,
    'back':    2,
    'confirm': 1,
    'abort':   1,
    'reload':  2,
    'save':    2,
    'push':    2,
    'pull':    2
  }
  saved_world_keywords: List[str] = [
    'Saved the game',  # 1.13+
    'Saved the world',  # 1.12-
  ]