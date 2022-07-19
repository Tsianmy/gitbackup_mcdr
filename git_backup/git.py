import os
import sys
import subprocess

from git_backup.utils import debug_message, log_info, log_warning, run_sh_cmd, get_format_time

def setup_git(config, logger=None):
  # check git
  ecode, out = run_sh_cmd('{git} --version'.format(git=config.git_path), config.debug)
  if ecode != 0:
    raise RuntimeError('Can not found git at "{}"'.format(config.git_path))
  log_info(logger, out.strip())

  if not os.path.isdir(config.backup_path):
    os.makedirs(config.backup_path)

  def _run_git_cmd_hp(child, *args):
    ecode, out = run_git_cmd(config, child, *args)
    if ecode != 0:
      log_info(logger, f'git {out.strip()}')
      raise RuntimeError('Init git error({0}): {1}'.format(ecode, out))
    else:
      log_info(logger, out.strip())

  if not os.path.isdir(os.path.join(config.backup_path, '.git')):
    config.git_cfg['is_setup'] = False
    # init git
    log_info(logger, 'git is initing')
    _run_git_cmd_hp('init')
    _run_git_cmd_hp('config', 'user.email', '"{}"'.format(config.git_cfg['user_email']))
    _run_git_cmd_hp('config', 'user.name', '"{}"'.format(config.git_cfg['user_name']))
    _run_git_cmd_hp('config', 'credential.helper', 'store')
    _run_git_cmd_hp('config', 'core.autocrlf', 'false')
    _run_git_cmd_hp('config', 'core.sshCommand', '"{}"'.format(config.git_cfg['ssh_command']))
  else:
    _run_git_cmd_hp('config', 'user.email', '"{}"'.format(config.git_cfg['user_email']))
    _run_git_cmd_hp('config', 'user.name', '"{}"'.format(config.git_cfg['user_name']))
    _run_git_cmd_hp('config', 'core.sshCommand', '"{}"'.format(config.git_cfg['ssh_command']))

  log_info(logger, 'git email: ' + run_git_cmd(config, 'config', 'user.email')[1].strip())
  log_info(logger, 'git user: ' + run_git_cmd(config, 'config', 'user.name')[1].strip())

  with open(os.path.join(config.backup_path, '.gitignore'), 'w') as fd:
    fd.write('# Make by GitBackUp at {}\n'.format(get_format_time()))
    fd.write('\n'.join(config.ignores))
  
  if not config.git_cfg['is_setup']:
    _run_git_cmd_hp('add', '--all')
    _run_git_cmd_hp('commit', '-m', '"{}=Setup commit"'.format(get_format_time()))
  else:    
    _run_git_cmd_hp('clean', '-df')
    _run_git_cmd_hp('restore', '.')

  try:
    _run_git_cmd_hp('branch', config.git_cfg['branch_name'])
  except: pass
  _run_git_cmd_hp('switch', config.git_cfg['branch_name'])

  # push
  if config.git_cfg['use_remote']:
    try:
      _run_git_cmd_hp('remote', 'add', config.git_cfg['remote_name'], config.git_cfg['remote'])
    except: pass
    ecode, out = run_git_cmd(config, 'remote', 'get-url', config.git_cfg['remote_name'])
    if ecode != 0 or out.strip() != config.git_cfg['remote']:
      log_info(logger, 'new url: ' + config.git_cfg['remote'])
      _run_git_cmd_hp('remote', 'set-url', config.git_cfg['remote_name'], config.git_cfg['remote'])

    log_info(logger, 'git remote: {}'.format(config.git_cfg['remote']))

    try:
      _run_git_cmd_hp('pull', '--set-upstream', config.git_cfg['remote_name'], config.git_cfg['branch_name'])
    except: pass

    if not config.git_cfg['is_setup']:
      proc = subprocess.Popen(
        '{git} -C {path} push -u {remote_name} {branch}'.format(
          git=config.git_path, path=config.backup_path,
          remote_name=config.git_cfg['remote_name'], branch=config.git_cfg['branch_name']),
        shell=True,
        stdout=sys.stdout, stderr=sys.stdout, stdin=sys.stdin,
        bufsize=-1)
      ecode = proc.wait()
      if ecode is not None and ecode != 0:
        raise RuntimeError('first push error')

  config.git_cfg['is_setup'] = True

def run_git_cmd(config, child: str, *args):
  command = '{git} -C {path} --no-pager {child} {args}'.format(
    git=config.git_path, path=config.backup_path, child=child, args=' '.join(args))
  debug_message(config.debug, 'child:', type(child), child, 'args:', args)
  return run_sh_cmd(command, config.debug)