import mcdreforged.api.all as MCDR
import functools
import time
import os

from typing import Callable, Optional, Any
from git_backup import common as GL
from git_backup.constants import (Prefix, PLUGIN_ABBR,
                                  BACKUP_DONE_EVENT, RESTORE_DONE_EVENT)
from git_backup.git import run_git_cmd
from git_backup.utils import (debug_message, log_warning, tr, log_info, log_except, print_message,
                              mkdir, copy_files, rmtree, remove_files, get_format_time,
                              get_dir_size, format_dir_size)

def single_op(name: MCDR.RTextBase):
    def wrapper(func: Callable):
        @functools.wraps(func)
        def wrap(source: MCDR.CommandSource, *args, **kwargs):
            acq = GL.operation_lock.acquire(blocking=False)
            if acq:
                try:
                    func(source, *args, **kwargs)
                finally:
                    GL.operation_lock.release()
            else:
                print_message(source, tr('lock.warning', name))
        return wrap
    return wrapper

@single_op(tr('operations.create'))
def create_backup(source: MCDR.CommandSource, comment: Optional[str], config, logger=None):
    comment = ('"{date}"' if comment is None else '"{date}={comment}"').format(
        date=get_format_time(), comment=comment)
    try:
        GL.game_saved = False
        if config.turn_off_auto_save:
            source.get_server().execute('save-off')
        source.get_server().execute('save-all flush')
        while not GL.game_saved:
            time.sleep(0.01)
            if GL.plugin_unloaded:
                print_message(source, tr('create_backup.abort.plugin_unload'), tell=False)
                return

        # start backup
        print_message(source, tr('create_backup.start'), tell=False)
        start_time = time.time()

        mkdir(config.backup_path)
        for file in config.need_backup:
            copy_files(config.server_path, config.backup_path, file, config.ignores,
                       logger=logger)
        print_message(source, tr('create_backup.commit'), tell=False)
        run_git_cmd(config, 'add', '--all')
        ecode, out = run_git_cmd(config, 'commit', '-m', comment)
        if ecode != 0:
            print_message(source, f'{out}', tell=False)
            raise RuntimeError()

        ecode, out = run_git_cmd(config, 'gc')
        if ecode != 0:
            print_message(source, f'{out}', tell=False)
            raise RuntimeError()

        # done
        end_time = time.time()
        print_message(source, tr('create_backup.success', round(end_time - start_time, 1)), tell=False)
        
    except Exception as e:
        log_except(logger, f'[{PLUGIN_ABBR}] Error creating backup')
        print_message(source, tr('create_backup.fail', e), tell=False)
    else:
        source.get_server().dispatch_event(BACKUP_DONE_EVENT, (source,))
    finally:
        if config.turn_off_auto_save:
            source.get_server().execute('save-on')

@single_op(tr('operations.push'))
def push_backup(source: MCDR.CommandSource, config, logger=None):
    if not config.git_cfg['use_remote']:
        print_message(source, 'Not allowed remote', tell=False)
        return
    print_message(source, tr('push_backup.push'), tell=False)
    ecode, out = run_git_cmd(config, 'push', '-f', '-q')
    if ecode != 0:
        print_message(source, tr('push_backup.fail', out), tell=False)
        return

    config.last_push_time = time.time()
    print_message(source, tr('push_backup.success', out), tell=False)

@single_op(tr('operations.restore'))
def restore_backup(source: MCDR.CommandSource, slot_info: tuple, config, logger=None):
    back_wait_time = config.back_wait_time
    slot = None
    try:
        slot, date, comment = slot_info
        print_message(source, tr('do_restore.countdown.intro', back_wait_time), tell=False)
        for countdown in range(1, back_wait_time):
            print_message(source, command_run(
                tr('do_restore.countdown.text', back_wait_time - countdown, slot[:10], date, comment),
                tr('do_restore.countdown.hover'),
                f'{Prefix} abort'
            ), tell=False)
            for _ in range(10):
                time.sleep(0.1)
                if GL.abort_restore:
                    print_message(source, tr('do_restore.abort'), tell=False)
                    return

        source.get_server().stop()
        log_info(logger, 'Wait for server to stop')
        source.get_server().wait_for_start()

        log_info(logger, 'Backup current world to avoid idiot')
        rmtree(config.cache_path)
        mkdir(config.cache_path)
        for file in config.need_backup:
            copy_files(config.server_path, config.cache_path, file, config.ignores,
                       logger=logger)
        with open(os.path.join(config.cache_path, 'info.txt'), 'w') as f:
            f.write('Overwrite time: {}\n'.format(get_format_time()))
            f.write('Confirmed by: {}'.format(source))

        ecode, out = run_git_cmd(config, 'clean', '-df')
        if ecode != 0:
            raise RuntimeError(f'Cleaning untracked files unsuccessfully, error {out}')
        ecode, out = run_git_cmd(config, 'reset', '--hard', slot)
        log_info(logger, f'{out}')
        if ecode == 0:
            # if os.path.exists(config.cache_path):
            # 	rmtree(config.cache_path)
            for file in config.need_backup:
                if file in ('.gitignore', '.git'):
                    continue
                remove_files(config.server_path, file, logger)
                copy_files(config.backup_path, config.server_path, file, config.ignores,
                           logger=logger)
            log_info(logger, f'Backup to {date}({comment})')

        log_info(logger, 'Starting server')
        source.get_server().start()
    except Exception as e:
        log_except(logger, f'triggered by {source}\n{e}')
        print_message(source, f'Fail to restore backup to slot {slot}', tell=False)
    else:
        source.get_server().dispatch_event(RESTORE_DONE_EVENT,
                                           (source, slot, date, comment))

def list_backup(source: MCDR.CommandSource, config, limit: int = None):
    ecode, out = run_git_cmd(config, 'log', '--pretty=oneline', '--no-decorate', '' if limit is None else '-{}'.format(limit))
    if ecode != 0:
        print_message(source, out, tell=False)
        return
    lines = out.splitlines()

    print_message(source, tr('list_backup.title'), prefix='')

    backup_size = get_dir_size(config.backup_path)

    latest = None
    debug_message(config.debug, 'whiling lines', len(lines))
    for i, l in enumerate(lines):
        debug_message(config.debug, 'parsing line:', i, ':', l)
        slot_idx = i + 1
        slot, date, comment = parse_backup_info(l)
        slot = slot[:10]
        slot_info = format_slot_info(slot, date, comment)
        # noinspection PyTypeChecker
        header = MCDR.RTextList(
            MCDR.RText(tr('list_backup.slot.header', slot_idx)),
            ' ',
        )
        text = MCDR.RTextList(
            slot_info,
            command_run(
                MCDR.RText('[▷] ', color=MCDR.RColor.green),
                tr('list_backup.slot.restore', slot),
                f'{Prefix} back {slot}'
            )
        )
        if i == 0:
            latest = text

        text = header + text
        print_message(source, text, prefix='')
    if latest is not None:
        latest = MCDR.RTextList(
            MCDR.RText(tr('list_backup.slot.header', 'latest')),
            ' ',
            latest
        )
        print_message(source, latest, prefix='')

    print_message(source, tr('list_backup.total_space', format_dir_size(backup_size)), prefix='')

@single_op(tr('operations.prune'))
def prune_backup(source: MCDR.CommandSource, config, logger=None):
    try:
        print_message(source, tr('prune_backup.start'), tell=False)

        ecode, out = run_git_cmd(config, 'reflog', 'expire --expire-unreachable=now --all')
        if ecode != 0:
            print_message(logger, out, tell=False)
            raise RuntimeError()
        ecode, out = run_git_cmd(config, 'gc', '--prune=now')
        if ecode != 0:
            print_message(logger, out, tell=False)
            raise RuntimeError()
        
        backup_size = format_dir_size(get_dir_size(config.backup_path))

        print_message(source, tr('prune_backup.success', backup_size), tell=False)
    except:
        print_message(source, tr('prune_backup.fail'), tell=False)

def command_run(message: Any, text: Any, command: str) -> MCDR.RTextBase:
    fancy_text = message.copy() if isinstance(message, MCDR.RTextBase) else MCDR.RText(message)
    return fancy_text.set_hover_text(text).set_click_event(MCDR.RAction.run_command, command)

def parse_backup_info(line: str):
    slot, cmn = line.split(' ', 1)
    a = cmn.split('=', 1)
    date, comment = a if len(a) == 2 else (a[0], '')
    return slot, date, comment

def get_backup_info(config, bid: str or int):
    use_hash = True
    bid_ = bid
    if isinstance(bid, int):
        use_hash = False
        bid_ = '-{}'.format(bid_)
    elif not isinstance(bid, str):
        raise TypeError('bid must be "int" or "str"')
    ecode, out = run_git_cmd(config, 'log', '--pretty=oneline', '--no-decorate', bid_, '--')
    if ecode != 0:
        raise RuntimeError('Get log error: ({0}){1}'.format(ecode, out))
    lines = out.splitlines()

    if use_hash:
        if len(lines) == 0:
            raise RuntimeError('Can not found commit by hash "{}"'.format(bid))
        return parse_backup_info(lines[0])
    if len(lines) < bid:
        raise RuntimeError('Index {} is out of range'.format(bid))
    return parse_backup_info(lines[bid - 1])

def format_slot_info(slot, date, comment) -> Optional[MCDR.RTextBase]:
    if comment is None or len(comment) == 0:
        comment = tr('empty_comment')
    return tr('slot_info', slot, date, comment)